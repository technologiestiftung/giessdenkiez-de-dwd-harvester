import shutil
from datetime import datetime
import psycopg2.extras
import psycopg2
import logging
import os
import math
import boto3
import requests
import json
import tempfile

logging.root.setLevel(logging.INFO)

# database connection
pg_server = os.getenv("PG_SERVER")
pg_port = os.getenv("PG_PORT")
pg_username = os.getenv("PG_USER")
pg_password = os.getenv("PG_PASS")
pg_database = os.getenv("PG_DB")
dsn = f"host='{pg_server}' port={pg_port} user='{pg_username}' password='{pg_password}' dbname='{pg_database}'"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

try:
    conn = psycopg2.connect(dsn)
    logging.info("🗄 Database connection established")
except:
    logging.error("❌Could not establish database connection")
    conn = None


def check_file_exists_in_supabase_storage(file_name):
    url = f"{SUPABASE_URL}/storage/v1/object/info/public/{SUPABASE_BUCKET_NAME}/{file_name}"
    response = requests.get(url)
    return response.status_code == 200


def upload_file_to_supabase_storage(file_path, file_name):
    try:
        file = open(file_path, "rb")
        file_url = (
            f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET_NAME}/{file_name}"
        )
        r = (
            requests.put
            if check_file_exists_in_supabase_storage(file_name)
            else requests.post
        )
        response = r(
            file_url,
            files={"file": file},
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "ContentType": "application/geo+json",
                "AcceptEncoding": "gzip, deflate, br",
            },
        )

        if response.status_code == 200:
            logging.info("✅ Uploaded {} to supabase storage".format(file_name))
        else:
            logging.error(response.status_code)
            logging.error(response.content)
            logging.error(
                "❌ Could not upload {} to supabase storage".format(file_name)
            )

    except Exception as error:
        logging.error(error)
        logging.error("❌ Could not upload {} supabase storage".format(file_name))


path = tempfile.mkdtemp()

current_year = datetime.now().year

with conn.cursor() as cur:
    # WARNING: The db is still mislabeled lat <> lng
    logging.info("Fetching trees from database...")
    cur.execute(
        "SELECT trees.id, trees.lat, trees.lng, trees.radolan_sum, trees.pflanzjahr FROM trees WHERE ST_CONTAINS(ST_SetSRID (( SELECT ST_EXTENT (geometry) FROM radolan_geometry), 4326), trees.geom)"
    )
    trees = cur.fetchall()
    trees_head = "id,lng,lat,radolan_sum,age"
    trees_csv = trees_head
    pLimit = math.ceil(len(trees) / 4)
    logging.info(f"Creating trees.csv file for {len(trees)} trees")
    for tree in trees:
        newLine = "\n"
        newLine += "{},{},{},{}".format(tree[0], tree[1], tree[2], tree[3])
        if tree[4] == 0:  # Invalid "pflanzjahr" column is reported as 0
            newLine += ","
        else:
            newLine += ",{}".format(int(current_year) - int(tree[4]))
        trees_csv += newLine
        
    text_file = open(path + "trees.csv", "w")
    n = text_file.write(trees_csv)
    text_file.close()
    n = None

    upload_file_to_supabase_storage(path + "trees.csv", "trees.csv")

    # send the updated csv to mapbox
    # get upload credentials
    try:
        url = "https://api.mapbox.com/uploads/v1/{}/credentials?access_token={}".format(
            os.getenv("MAPBOXUSERNAME"), os.getenv("MAPBOXTOKEN")
        )
        response = requests.post(url)
        s3_credentials = json.loads(response.content)

        # upload latest data
        s3mapbox = boto3.client(
            "s3",
            aws_access_key_id=s3_credentials["accessKeyId"],
            aws_secret_access_key=s3_credentials["secretAccessKey"],
            aws_session_token=s3_credentials["sessionToken"],
        )
        s3mapbox.upload_file(
            path + "trees.csv", s3_credentials["bucket"], s3_credentials["key"]
        )

        # tell mapbox that new data has arrived
        url = "https://api.mapbox.com/uploads/v1/{}?access_token={}".format(
            os.getenv("MAPBOXUSERNAME"), os.getenv("MAPBOXTOKEN")
        )
        payload = '{{"url":"http://{}.s3.amazonaws.com/{}","tileset":"{}.{}","name":"{}"}}'.format(
            s3_credentials["bucket"],
            s3_credentials["key"],
            os.getenv("MAPBOXUSERNAME"),
            os.getenv("MAPBOXTILESET"),
            os.getenv("MAPBOXLAYERNAME"),
        )
        headers = {
            "content-type": "application/json",
            "Accept-Charset": "UTF-8",
            "Cache-Control": "no-cache",
        }
        response = requests.post(url, data=payload, headers=headers)

        # TODO: Check response status codes
        # TODO: Check upload status until error or complete

    except Exception as error:
        logging.error("could not upload tree data to mapbox for vector tiles")
        logging.error(error)
        exit(1)

    trees_csv = None
    csv_data = None

# remove all temporary files
shutil.rmtree(path)

conn.close()
