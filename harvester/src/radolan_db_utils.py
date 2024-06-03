import psycopg2
from datetime import datetime
from datetime import timedelta
import logging
import pytz


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


def upload_radolan_data_in_db(extracted_radolan_values, db_conn):
    """Uploads extracted radolon data into database

    Args:
        extracted_radolan_values (_type_): the radolon values to upload
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
            """
            INSERT INTO radolan_data (geom_id, value, measured_at)
            SELECT radolan_geometry.id, radolan_temp.value, radolan_temp.measured_at
            FROM radolan_geometry
            JOIN radolan_temp ON ST_WithIn(radolan_geometry.centroid, radolan_temp.geometry);
            """
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
