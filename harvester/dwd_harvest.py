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


def harvest_dwd(surrounding_shape_file, start_date, end_date, conn):
    """Starts harvesting DWD radolan data based on database given in 'conn'

    Args:
        start_date (datetime): first day of radolon data to harvest
        end_date (datetime): last day of radolon data to harvest
        surrounding_shape_file (_type_): shapefile for area of interest
        conn (_type_): database connection

    Returns:
        _type_: grid of radolan data for polygonized shapefile
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
                upload_radolan_data_in_db(extracted_radolan_values, conn)

        # After all db inserts, cleanup db, build grid
        _ = cleanup_radolan_entries(conn)
        radolan_grid = build_radolan_grid(conn)

        return radolan_grid
