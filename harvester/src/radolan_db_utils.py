import calendar
import psycopg2
from datetime import datetime, time
from datetime import timedelta
import logging
import pytz
from dateutil.relativedelta import relativedelta


def get_first_and_last_day_for_harvest_round(month: int, year: int, db_conn):
    utc_tz = pytz.timezone("UTC")

    # Check if aggregation exists
    existing_aggregation = get_existing_month_aggregation(month, year, db_conn)
    last_harvest_day_in_db = existing_aggregation[3] if existing_aggregation else None

    # Get year and month from the datetime object
    last_day_of_month_number = calendar.monthrange(year, month)[1]

    last_day_of_month = datetime(year, month, last_day_of_month_number).replace(
        tzinfo=utc_tz
    )

    # Create a new datetime object for the last day of the month
    first_harvest_day_for_this_round = datetime(year, month, 1).replace(tzinfo=utc_tz)
    last_harvest_day_for_this_round = last_day_of_month

    # If the last harvest day in the DB is smaller than the last day of the month, start from the last harvest day
    if last_harvest_day_in_db != None and (
        last_harvest_day_in_db < last_day_of_month_number
    ):
        first_harvest_day_for_this_round = datetime(
            year, month, last_harvest_day_in_db + 1
        ).replace(tzinfo=utc_tz)

    # If the last day of the month is in the future, set it to yesterday (because the data for today is not available yet)
    if datetime.now(utc_tz) < last_day_of_month:
        last_harvest_day_for_this_round = datetime.combine(
            datetime.now(utc_tz) - timedelta(days=1), time(23, 59, 59)
        ).replace(tzinfo=utc_tz)

    if last_harvest_day_for_this_round < first_harvest_day_for_this_round:
        last_harvest_day_for_this_round = first_harvest_day_for_this_round

    return (
        first_harvest_day_for_this_round,
        last_harvest_day_for_this_round,
        last_day_of_month,
    )


def get_existing_month_aggregation(month: int, year: int, db_conn):
    logging.info(f"Getting existing month aggregation for {month}-{year}...")
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM monthly_aggregated_radolan_data WHERE month = %s AND year = %s",
            [month, year],
        )
        aggregation = cur.fetchone()

        if aggregation == None:
            return None

        return aggregation


def get_months_without_aggregations(limit_months: int, db_conn):
    """Gets months without aggregations

    Args:
        db_conn (_type_): the database connection
    Returns:
        _type_: array containing months without aggregations
    """
    logging.info(f"Getting months without aggregations...")
    utc_tz = pytz.timezone("UTC")
    now_time = datetime.now(utc_tz)
    oldest_month_to_harvest = datetime.combine(
        now_time - relativedelta(months=limit_months), datetime.min.time()
    ).replace(tzinfo=utc_tz)

    iterate_time = oldest_month_to_harvest
    months_to_harvest = []

    while iterate_time < now_time:
        first_day_of_iterate_time = iterate_time.replace(day=1)
        iterate_year = first_day_of_iterate_time.year
        iterate_month = first_day_of_iterate_time.month
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM monthly_aggregated_radolan_data WHERE month = %s AND year = %s;",
                [iterate_month, iterate_year],
            )
            existing_aggregation = cur.fetchone()

            if existing_aggregation == None:
                cur.execute(
                    "INSERT INTO monthly_aggregated_radolan_data (month, year, harvesting_finished) VALUES (%s, %s, %s);",
                    [iterate_month, iterate_year, False],
                )
                db_conn.commit()
                months_to_harvest.append((iterate_month, iterate_year))
            else:
                if existing_aggregation[6] == False:
                    months_to_harvest.append((iterate_month, iterate_year))

        iterate_time = iterate_time + relativedelta(months=1)

    logging.info(f"Months to harvest: {months_to_harvest}")
    return months_to_harvest


def get_start_end_harvest_dates(db_conn):
    """Gets first and last day for harvesting

    Args:
        db_conn (_type_): the database connection
    Returns:
        _type_: array containing start_date and end_date
    """
    logging.info(f"Getting first and last day for harvesting...")
    with db_conn.cursor() as cur:
        # The DWD Harvester is scheduled to run at 00:01 Europe/Berlin every day
        # We want all weather data up to the day before the current day
        berlin_tz = pytz.timezone("Europe/Berlin")
        now_berlin_time = datetime.now(berlin_tz)
        cur.execute("SELECT collection_date FROM radolan_harvester WHERE id = 1")
        last_date = cur.fetchone()[0]
        start_date = datetime.combine(last_date, datetime.min.time())
        end_date = datetime.combine(
            now_berlin_time - timedelta(days=1), datetime.max.time()
        )
        logging.info(f"Start date: {start_date}, End date: {end_date}")
        return [start_date, end_date]


def upload_radolan_data_in_db(extracted_radolan_values, table_name, db_conn):
    """Uploads extracted radolon data into database

    Args:
        extracted_radolan_values (_type_): the radolon values to upload
        table_name (_type_): the name of the target table
        db_conn (_type_): the database connection
    """
    logging.info(f"Uploading radolan data to database...")
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM radolan_temp;")
        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO radolan_temp (geometry, value, measured_at)
            VALUES (ST_Multi(ST_Transform(ST_GeomFromText(%s, 3857), 4326)), %s, %s);
            """,
            extracted_radolan_values,
        )
        cur.execute(
            f"""
            INSERT INTO {table_name} (geom_id, value, measured_at)
            SELECT radolan_geometry.id, radolan_temp.value, radolan_temp.measured_at
            FROM radolan_geometry
            JOIN radolan_temp ON ST_WithIn(radolan_geometry.centroid, radolan_temp.geometry);
            """
        )
        db_conn.commit()


def aggregate_monthly_radolan_data_in_db(
    month, year, last_harvest_day, finished, db_conn
):
    """Aggregates monthly radolon data in database

    Args:
        month (_type_): the month to aggregate the extracted radolan values for
        db_conn (_type_): the database connection
    """
    logging.info(f"Aggregating radolan data for {month}...")
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                avg(sum_rain.avg_rain) as avg_rain_aggregated
            FROM (
                SELECT
                    geom_id,
                    sum(value) AS avg_rain
                FROM
                    monthly_radolan_data_temp
                GROUP BY
                    geom_id) AS sum_rain;
                    """
        )
        radolan_one_tenth_mm_per_sm2 = cur.fetchone()[0]
        radolan_liters_per_sm2 = radolan_one_tenth_mm_per_sm2 / 10
        cur.execute(
            f"""
                UPDATE monthly_aggregated_radolan_data SET last_harvest_day = %s, harvesting_finished = %s, avg_precipitation_liters_per_sm2 = %s
                WHERE month = %s AND year = %s;
            """,
            (last_harvest_day, finished, radolan_liters_per_sm2, month, year),
        )
        db_conn.commit()


def update_trees_in_database(radolan_grid, db_conn):
    """Updates tree radolon data in database

    Args:
        radolan_grid (_type_): the radolon value grid to use for updating the trees
        db_conn (_type_): the database connection
    """
    logging.info(f"Updating trees in database...")
    with db_conn.cursor() as cur:
        psycopg2.extras.execute_batch(
            cur,
            """
            UPDATE trees
            SET radolan_days = %s, radolan_sum = %s
            WHERE ST_CoveredBy(geom, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326));
            """,
            radolan_grid,
        )
        db_conn.commit()

    with db_conn.cursor() as cur:
        psycopg2.extras.execute_batch(
            cur,
            """
            UPDATE trees
            SET radolan_days = %s, radolan_sum = %s
            WHERE trees.radolan_sum IS NULL
            AND ST_CoveredBy(geom, ST_Buffer(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 0.0002));
            """,
            radolan_grid,
        )
        db_conn.commit()


def purge_all_monthly_radolan_entries(db_conn):
    """Purge all radolon data in database

    Args:
        db_conn (_type_): the database connection
    """
    logging.info(f"Purge all monthly radolon data in database...")
    with db_conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM monthly_radolan_data_temp where true;
            """
        )
        db_conn.commit()


def cleanup_radolan_entries(limit_days, db_conn):
    """Cleanup radolon data in database (old and duplicated data)

    Args:
        limit_days (number): number of previous days to keep radolan data for
        db_conn (_type_): the database connection
    """
    logging.info(f"Cleanup old and duplicated datat in database...")
    with db_conn.cursor() as cur:
        # Delete duplicated data
        cur.execute(
            """
            DELETE FROM radolan_data AS a USING radolan_data AS b
            WHERE a.id < b.id AND a.geom_id = b.geom_id
            AND a.measured_at = b.measured_at
            """
        )
        # Delete old data
        cur.execute(
            """
            DELETE
            FROM radolan_data
            WHERE measured_at < NOW() - INTERVAL '{} days'
            """.format(
                limit_days
            )
        )
        db_conn.commit()


def update_harvest_dates(start_date, end_date, db_conn):
    """Update last harvest date

    Args:
        start_date (datetime): first day of radolon data to harvest
        end_date (datetime): last day of radolon data to harvest
        db_conn (_type_): the database connection
    """
    logging.info(f"Update last harvest date...")
    with db_conn.cursor() as cur:
        cur.execute(
            """
            UPDATE radolan_harvester SET end_date = '{}', collection_date = '{}', start_date = '{}' WHERE id = 1;
            """.format(
                end_date, end_date, start_date
            )
        )
        db_conn.commit()
