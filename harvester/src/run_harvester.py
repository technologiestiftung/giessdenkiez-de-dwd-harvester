import sys
import psycopg2.extras
import psycopg2
from dotenv import load_dotenv
import logging
import os
from radolan_db_utils import update_trees_in_database
from dwd_harvest import harvest_dwd
from radolan_db_utils import (
    get_start_end_harvest_dates,
)
from mapbox_tree_update import update_mapbox_tree_layer

# Set up logging
logging.basicConfig()
logging.root.setLevel(logging.INFO)

# Load the environmental variables
load_dotenv()

# Check if all required environmental variables are accessible
for env_var in [
    "PG_DB",
    "PG_PORT",
    "PG_USER",
    "PG_PASS",
    "SUPABASE_URL",
    "SUPABASE_BUCKET_NAME",
    "SUPABASE_SERVICE_ROLE_KEY",
    "LIMIT_DAYS",
    "MAPBOXUSERNAME",
    "MAPBOXTOKEN",
    "MAPBOXTILESET",
    "MAPBOXLAYERNAME",
]:
    if env_var not in os.environ:
        logging.error("❌Environmental Variable {} does not exist".format(env_var))
        sys.exit(1)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
LIMIT_DAYS = int(os.getenv("LIMIT_DAYS"))
SKIP_MAPBOX = os.getenv("SKIP_MAPBOX") == "True"
MAPBOX_USERNAME = os.getenv("MAPBOXUSERNAME")
MAPBOX_TOKEN = os.getenv("MAPBOXTOKEN")
MAPBOX_TILESET = os.getenv("MAPBOXTILESET")
MAPBOX_LAYERNAME = os.getenv("MAPBOXLAYERNAME")
PG_SERVER = os.getenv("PG_SERVER")
PG_PORT = os.getenv("PG_PORT")
PG_USER = os.getenv("PG_USER")
PG_PASS = os.getenv("PG_PASS")
PG_DB = os.getenv("PG_DB")


# Establish database connection
try:
    database_connection_str = f"host='{PG_SERVER}' port={PG_PORT} user='{PG_USER}' password='{PG_PASS}' dbname='{PG_DB}'"
    database_connection = psycopg2.connect(database_connection_str)
    logging.info("🗄 Database connection established")
except:
    logging.error("❌Could not establish database connection")
    database_connection = None
    sys.exit(1)

# Start harvesting DWD data
start_date, end_date = get_start_end_harvest_dates(database_connection)
radolan_grid = harvest_dwd(
    surrounding_shape_file="./assets/buffer.shp",
    start_date=start_date,
    end_date=end_date,
    limit_days=LIMIT_DAYS,
    database_connection=database_connection,
)

# Update trees in database
update_trees_in_database(radolan_grid, database_connection)

# Update Mapbox layer
if not SKIP_MAPBOX:
    update_mapbox_tree_layer(
        MAPBOX_USERNAME,
        MAPBOX_TOKEN,
        MAPBOX_TILESET,
        MAPBOX_LAYERNAME,
        SUPABASE_URL,
        SUPABASE_BUCKET_NAME,
        SUPABASE_SERVICE_ROLE_KEY,
        database_connection,
    )
