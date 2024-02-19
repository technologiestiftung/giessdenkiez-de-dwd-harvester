from datetime import timedelta
import urllib.request
import logging
import os
import gzip
import tarfile
import shutil

# We are using Radolan data from DWD
# https://www.dwd.de/DE/leistungen/radolan/radolan.html
# https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/radolan/recent/asc/DESCRIPTION_gridsgermany-hourly-radolan-recent-asc_en.pdf
url = f"https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/radolan/recent/asc"


def download_radolan_data(start_date, end_date, path):
    """Download Radolan data from DWD
    Args:
        start_date (str): The first day to download Radolan data for
        end_date (str): The last day to download Radolan data for
        path (str): The full path where the downloaded files should be stored
    Returns:
        list[str]: List of file paths of the downloaded files. Each file contains zipped Radolan data files for each hour of the day.
    """
    downloaded_files = []
    while start_date <= end_date:
        date_str = start_date.strftime("%Y%m%d")
        file_name = f"RW-{date_str}.tar.gz"
        download_url = f"{url}/{file_name}"
        dest_file = os.path.join(path, file_name)
        urllib.request.urlretrieve(download_url, dest_file)
        downloaded_files.append(dest_file)
        start_date += timedelta(days=1)
        logging.info(f"Downloading {download_url}...")

    return downloaded_files


def unzip_radolan_data(zipped_radar_files, root_path):
    """Extract the previously downloaded Radolan files to get the hourly Radolan files
    Args:
        zipped_radar_files (list[str]): List of zipped Radolan files
        root_path (str): Path where the extracted files should be stored
    Returns:
        list[str]: List of paths to the extracted Radolan files. Each file contains the hourly Radolan data.
    """
    for _, filename in enumerate(zipped_radar_files):
        if filename.endswith(".tar.gz"):
            # Unzip
            with gzip.open(filename, "rb") as f_in:
                with open(filename[:-3], "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(filename)

            # Untar
            with tarfile.open(filename[:-3], "r") as tar:
                temp_path = filename[:-7]
                os.makedirs(temp_path, exist_ok=True)
                tar.extractall(path=temp_path)
                tar.close()

            os.remove(filename[:-3])
            logging.info(f"Extracting hourly Radolan files from: {filename}...")

    unzipped_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(root_path)
        for file in files
    ]

    return unzipped_files
