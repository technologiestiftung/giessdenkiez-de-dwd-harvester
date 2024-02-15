import geopandas
from shapely.wkt import dumps
import subprocess
import shutil
import gzip
import tarfile
import urllib.request
from datetime import timedelta
from datetime import datetime
import psycopg2.extras
import psycopg2
from dotenv import load_dotenv
import logging
import os
from download_radar_data import download_radolan_data, extract_radolan_data
from project_radolan_data import project_radolan_data, polygonize_data
import tempfile

# setting up logging
logging.basicConfig()
LOGGING_MODE = None
if "LOGGING" in os.environ:
    LOGGING_MODE = os.getenv("LOGGING")
    if LOGGING_MODE == "ERROR":
        logging.root.setLevel(logging.ERROR)
    elif LOGGING_MODE == "WARNING":
        logging.root.setLevel(logging.WARNING)
    elif LOGGING_MODE == "INFO":
        logging.root.setLevel(logging.INFO)
    else:
        logging.root.setLevel(logging.NOTSET)
else:
    logging.root.setLevel(logging.NOTSET)

# loading the environmental variables
load_dotenv()

# check if all required environmental variables are accessible
for env_var in [
    "PG_DB",
    "PG_PORT",
    "PG_USER",
    "PG_PASS",
    "SUPABASE_URL",
    "SUPABASE_BUCKET_NAME",
    "SUPABASE_SERVICE_ROLE_KEY",
]:
    if env_var not in os.environ:
        logging.error("❌Environmental Variable {} does not exist".format(env_var))

# database connection

pg_server = os.getenv("PG_SERVER")
pg_port = os.getenv("PG_PORT")
pg_username = os.getenv("PG_USER")
pg_password = os.getenv("PG_PASS")
pg_database = os.getenv("PG_DB")

dsn = f"host='{pg_server}' port={pg_port} user='{pg_username}' password='{pg_password}' dbname='{pg_database}'"

logging.info("🆙 Starting harvester v0.5")
# get last day of insert
last_date = None

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

try:
    conn = psycopg2.connect(dsn)
    logging.info("🗄 Database connection established")
except:
    logging.error("❌Could not establish database connection")
    conn = None

with tempfile.TemporaryDirectory() as temp_dir:

    # Download daily Radolan files from DWD for whole Germany
    # https://www.dwd.de/DE/leistungen/radolan/radolan.html
    # https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/radolan/recent/asc/DESCRIPTION_gridsgermany-hourly-radolan-recent-asc_en.pdf
    with conn.cursor() as cur:
        cur.execute("SELECT collection_date FROM radolan_harvester WHERE id = 1")
        last_date = cur.fetchone()[0]
    end_date = datetime.now() - timedelta(days=1)
    start_date = datetime.combine(last_date, datetime.min.time())
    daily_radolan_files = download_radolan_data(start_date, end_date, temp_dir)

    # Extract downloaded daily Radolan files into hourly Radolan data files
    hourly_radolan_files = extract_radolan_data(daily_radolan_files, temp_dir)
    print(hourly_radolan_files)

    # Project data for each hourly Radolan file
    for hourly_radolan_file in hourly_radolan_files:

        with tempfile.TemporaryDirectory() as hourly_temp_dir:
            projected_radolan_geotiff = project_radolan_data(
                hourly_radolan_file, "./assets/buffer.shp", hourly_temp_dir
            )
            print(projected_radolan_geotiff)

            polygonized_radolan = polygonize_data(
                projected_radolan_geotiff, hourly_temp_dir
            )
            print(projected_radolan_geotiff)

conn.close()
