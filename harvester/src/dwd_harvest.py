from datetime import datetime
import tempfile
from download_radolan_data import download_radolan_data, unzip_radolan_data
from project_radolan_data import project_radolan_data, polygonize_data
from extract_radolan_data import extract_radolan_data_from_shapefile
from radolan_db_utils import (
    upload_radolan_data_in_db,
    cleanup_radolan_entries,
)
from build_radolan_grid import build_radolan_grid


def harvest_dwd(
    surrounding_shape_file, start_date, end_date, limit_days, database_connection
):
    """Starts harvesting DWD radolan data based on start_date and end_date.
       Builds a grid of radolan data containing hourly radolan data for every polygon in the grid.
    Args:
        surrounding_shape_file (shapefile): shapefile for area of interest
        start_date (datetime): first day of radolon data to harvest
        end_date (datetime): last day of radolon data to harvest
        limit_days (number): number of previous days to harvest data for
        database_connection (_type_): database connection
    Returns:
        _type_: grid of radolan data
    """
    with tempfile.TemporaryDirectory() as temp_dir:

        # Download daily Radolan files from DWD for whole Germany
        daily_radolan_files = download_radolan_data(start_date, end_date, temp_dir)

        # Extract downloaded daily Radolan files into hourly Radolan data files
        hourly_radolan_files = unzip_radolan_data(daily_radolan_files, temp_dir)

        # Process all hourly Radolan files
        for hourly_radolan_file in hourly_radolan_files:

            filename = hourly_radolan_file.split("/")[-1]
            measured_at_timestamp = datetime.strptime(filename, "RW_%Y%m%d-%H%M.asc")

            with tempfile.TemporaryDirectory() as hourly_temp_dir:

                # Generate projected GeoTIFF file containing projected data for given shape file only
                projected_radolan_geotiff = project_radolan_data(
                    hourly_radolan_file, surrounding_shape_file, hourly_temp_dir
                )

                # Polygonize given GeoTIFF file
                polygonized_radolan = polygonize_data(
                    projected_radolan_geotiff, hourly_temp_dir
                )

                # Extract Radolan data
                extracted_radolan_values = extract_radolan_data_from_shapefile(
                    polygonized_radolan, measured_at_timestamp
                )

                # Update Radolan data in DB
                upload_radolan_data_in_db(extracted_radolan_values, database_connection)

        # After all database inserts, cleanup db
        _ = cleanup_radolan_entries(limit_days, database_connection)

        # Build radolan grid based on database values
        radolan_grid = build_radolan_grid(limit_days, database_connection)

        return radolan_grid
