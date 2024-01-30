import os
import requests
import json
import tempfile
import shutil
import subprocess
from datetime import datetime
import psycopg2
import logging
from tqdm import tqdm
from uploadAndRegenerateLayer import uploadAndRegenerateLayer
from generateCylinderGeojson import generateCylinderGeojson

# Set the log level
logging.root.setLevel(logging.INFO)

SKIP_MAPBOX = os.getenv("SKIP_MAPBOX")

# Database connection parameters
pg_server = os.getenv("PG_SERVER")
pg_port = os.getenv("PG_PORT")
pg_username = os.getenv("PG_USER")
pg_password = os.getenv("PG_PASS")
pg_database = os.getenv("PG_DB")
dsn = f"host='{pg_server}' port={pg_port} user='{pg_username}' password='{pg_password}' dbname='{pg_database}'"

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


# Function to check if a file exists in Supabase storage
def check_file_exists_in_supabase_storage(file_name):
    url = f"{SUPABASE_URL}/storage/v1/object/info/public/{SUPABASE_BUCKET_NAME}/{file_name}"
    response = requests.get(url)
    return response.status_code == 200


# Function to upload a file to Supabase storage
def upload_file_to_supabase_storage(file_path, file_name):
    try:
        with open(file_path, "rb") as file:
            file_url = (
                f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET_NAME}/{file_name}"
            )
            http_method = (
                requests.put
                if check_file_exists_in_supabase_storage(file_name)
                else requests.post
            )
            response = http_method(
                file_url,
                files={"file": file},
                headers={
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "ContentType": "application/geo+json",
                    "AcceptEncoding": "gzip, deflate, br",
                },
            )

            if response.status_code == 200:
                logging.info(f"✅ Uploaded {file_name} to Supabase storage")
            else:
                logging.error(response.status_code)
                logging.error(response.content)
                logging.error(f"❌ Could not upload {file_name} to Supabase storage")

    except Exception as error:
        logging.error(error)
        logging.error(f"❌ Could not upload {file_name} to Supabase storage")


# Create a temporary directory
path = tempfile.mkdtemp()

# Get the current year
current_year = datetime.now().year

# Initialize the database connection
try:
    conn = psycopg2.connect(dsn)
    logging.info("🗄 Database connection established")
except Exception as e:
    logging.error("❌ Could not establish a database connection")
    conn = None

if conn is not None:
    with conn.cursor() as cur:
        logging.info("Fetching trees from the database...")
        # WARNING: The db is still mislabeled lat <> lng
        cur.execute(
            "SELECT trees.id, trees.lat, trees.lng, trees.radolan_sum, trees.pflanzjahr FROM trees WHERE ST_CONTAINS(ST_SetSRID (( SELECT ST_EXTENT (geometry) FROM radolan_geometry), 4326), trees.geom);"
        )
        trees = cur.fetchall()

        # Creating trees.csv file
        header = "id,lng,lat,radolan_sum,age"
        logging.info(f"Creating trees.csv file for {len(trees)} trees")

        lines = []
        for tree in tqdm(trees):
            age = int(current_year) - int(tree[4]) if tree[4] != 0 else ""
            line = "{},{},{},{},{}".format(tree[0], tree[1], tree[2], tree[3], age)
            lines.append(line)

        trees_csv = "\n".join([header] + lines)

        trees_csv_full_path = os.path.join(path, "trees.csv")
        trees_preprocessed_full_path = os.path.join(path, "trees-preprocessed.mbtiles")

        with open(trees_csv_full_path, "w") as out:
            out.write(trees_csv)

        geojson = generateCylinderGeojson(trees)
        geojson_full_path = os.path.join(path, "tree_cylinders.json")
        geojson_processed_full_path = os.path.join(path, "tree_cylinders.mbtiles")

        with open(geojson_full_path, "w") as out:
            json.dump(geojson, out)

        # Pre-process trees cylinders with tippecanoe
        logging.info("Preprocess tree_cylinders.json with tippecanoe...")
        subprocess.call(
            [
                "tippecanoe",
                "-zg",
                "-o",
                geojson_processed_full_path,
                "--force",
                "--drop-fraction-as-needed",
                geojson_full_path,
            ]
        )
        logging.info("Preprocess tree_cylinders.json with tippecanoe... Done.")
        upload_file_to_supabase_storage(
            geojson_processed_full_path, "tree-cylinders-preprocessed.mbtiles"
        )

        # Pre-process trees.csv with tippecanoe
        logging.info("Preprocess trees.csv with tippecanoe...")
        subprocess.call(
            [
                "tippecanoe",
                "-zg",
                "-o",
                trees_preprocessed_full_path,
                "--force",
                "--drop-fraction-as-needed",
                trees_csv_full_path,
            ]
        )
        logging.info("Preprocess trees.csv with tippecanoe... Done.")

        # Upload preprocessed data to Supabase storage
        upload_file_to_supabase_storage(
            trees_preprocessed_full_path, "trees-preprocessed.mbtiles"
        )

        # Send the updated CSV to Mapbox
        if SKIP_MAPBOX != "True":
            try:
                uploadAndRegenerateLayer(
                    trees_preprocessed_full_path,
                    os.getenv("MAPBOXUSERNAME"),
                    os.getenv("MAPBOXTILESET"),
                    os.getenv("MAPBOXLAYERNAME"),
                )
                uploadAndRegenerateLayer(
                    geojson_processed_full_path,
                    os.getenv("MAPBOXUSERNAME"),
                    os.getenv("MAPBOX_CYLINDER_TILESET"),
                    os.getenv("MAPBOX_CYLINDER_LAYERNAME"),
                )

            except Exception as error:
                logging.error("Could not upload tree data to Mapbox for vector tiles")
                logging.error(error)
                exit(1)
        else:
            logging.info("Skipping Mapbox Tileset generation.")

        # Clean up
        trees_csv = None
        csv_data = None

# Remove all temporary files
shutil.rmtree(path)

# Close the database connection
if conn is not None:
    conn.close()
