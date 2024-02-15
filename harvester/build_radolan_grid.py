from datetime import datetime
from datetime import timedelta


def build_radolan_grid(db_conn):
    print("Building radolan grid based on DB entries...")

    limit_days = 30

    # start date is 'limit_days' days before now, starting at 00h:50min:00s
    start_date = datetime.now() + timedelta(days=-limit_days)
    start_date = start_date.replace(hour=0, minute=50, second=0, microsecond=0)

    # end date is yesterday at 23h:50min:00s
    end_date = datetime.now() + timedelta(days=-1)
    end_date = end_date.replace(hour=23, minute=50, second=0, microsecond=0)

    grid = []
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                radolan_geometry.id AS geometry_id,
                ST_AsGeoJSON(radolan_geometry.geometry) AS geometry_geojson,
                ARRAY_AGG(radolan_data.measured_at) AS measured_at,
                ARRAY_AGG(radolan_data.value) AS value
            FROM
                radolan_geometry
                JOIN radolan_data ON radolan_geometry.id = radolan_data.geom_id
            WHERE
                radolan_data.measured_at > NOW() - INTERVAL '{} days'
            GROUP BY
                radolan_geometry.id,
                radolan_geometry.geometry;
            """.format(
                limit_days
            )
        )
        grid = cur.fetchall()
        db_conn.commit()

    # build clean, sorted arrays
    grid_radolan_values = []
    for cell in grid:
        measured_dates = cell[2]
        measured_radolan_values = cell[3]

        end_date = datetime.now() + timedelta(days=-1)
        end_date = end_date.replace(hour=23, minute=50, second=0, microsecond=0)
        start_date = datetime.now() + timedelta(days=-limit_days)
        start_date = start_date.replace(hour=0, minute=50, second=0, microsecond=0)
        radolan_values_for_cell = []
        while start_date <= end_date:
            found = False
            for date_index, date in enumerate(measured_dates):
                if start_date == date:
                    found = True
                    radolan_values_for_cell.append(measured_radolan_values[date_index])
            if found == False:
                radolan_values_for_cell.append(0)
            start_date += timedelta(hours=1)
        grid_radolan_values.append(radolan_values_for_cell)

    formatted_grid_radolan_values = []
    for cell_index, cell in enumerate(grid):
        formatted_grid_radolan_values.append(
            [
                grid_radolan_values[cell_index],
                sum(grid_radolan_values[cell_index]),
                cell[1],
            ]
        )

    return formatted_grid_radolan_values
