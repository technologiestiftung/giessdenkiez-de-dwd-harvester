import psycopg2.extras
import psycopg2
from dotenv import load_dotenv
import logging
import os
from radolan_db_utils import update_trees
from dwd_harvest import harvest_dwd
from radolan_db_utils import (
    get_start_end_harvest_dates,
)

# setting up logging
logging.basicConfig()
logging.root.setLevel(logging.INFO)

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

database_connection = f"host='{pg_server}' port={pg_port} user='{pg_username}' password='{pg_password}' dbname='{pg_database}'"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

try:
    conn = psycopg2.connect(database_connection)
    logging.info("🗄 Database connection established")
except:
    logging.error("❌Could not establish database connection")
    conn = None

# Start harvesting DWD
start_date, end_date = get_start_end_harvest_dates(conn)
radolan_grid = harvest_dwd(
    surrounding_shape_file="./assets/buffer.shp",
    start_date=start_date,
    end_date=end_date,
    conn=conn,
)

# Update trees
update_trees(radolan_grid, conn)
