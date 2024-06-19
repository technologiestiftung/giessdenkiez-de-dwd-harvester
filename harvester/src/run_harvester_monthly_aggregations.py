import sys
import psycopg2.extras
import psycopg2
from dotenv import load_dotenv
import logging
import os
from radolan_db_utils import get_months_without_aggregations
from dwd_harvest import harvest_dwd_monthly_aggregation

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
    "SURROUNDING_SHAPE_FILE",
]:
    if env_var not in os.environ:
        logging.error("❌Environmental Variable {} does not exist".format(env_var))
        sys.exit(1)

PG_SERVER = os.getenv("PG_SERVER")
PG_PORT = os.getenv("PG_PORT")
PG_USER = os.getenv("PG_USER")
PG_PASS = os.getenv("PG_PASS")
PG_DB = os.getenv("PG_DB")
SURROUNDING_SHAPE_FILE = os.getenv("SURROUNDING_SHAPE_FILE")

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
months_to_harvest = get_months_without_aggregations(
    limit_months=2, db_conn=database_connection
)

radolan_grid = harvest_dwd_monthly_aggregation(
    surrounding_shape_file=SURROUNDING_SHAPE_FILE,
    months_to_harvest=months_to_harvest,
    database_connection=database_connection,
)
