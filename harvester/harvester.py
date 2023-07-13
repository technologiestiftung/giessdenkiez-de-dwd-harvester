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
import sys
import math
import boto3
import requests
import json


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
for env_var in ["PG_DB", "PG_PORT", "PG_USER", "PG_PASS", "SUPABASE_URL", "SUPABASE_BUCKET_NAME", "SUPABASE_SERVICE_ROLE_KEY"]:
    if env_var not in os.environ:
        logging.error(
            "❌Environmental Variable {} does not exist".format(env_var))

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

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_BUCKET_NAME = os.getenv('SUPABASE_BUCKET_NAME')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


try:
    conn = psycopg2.connect(dsn)
    logging.info("🗄 Database connection established")
except:
    logging.error("❌Could not establish database connection")
    conn = None

with conn.cursor() as cur:
    cur.execute("SELECT collection_date FROM radolan_harvester WHERE id = 1")
    last_date = cur.fetchone()[0]

logging.info("Last harvest {}".format(last_date))

# create a temporary folder to store the downloaded DWD data
path = "/temp/"
if os.path.isdir(path) != True:
    os.mkdir(path)

# now download all zips starting from last date, until yesterday (DWD usually uploads the latest data at some point during the night)

enddate = datetime.now() + timedelta(days=-1)
date = datetime.combine(last_date, datetime.min.time())

while date <= enddate:
    url = 'https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/radolan/recent/asc/RW-{}.tar.gz'.format(
        date.strftime("%Y%m%d"))
    url_split = url.split("/")
    dest_name = url_split[len(url_split) - 1]
    dest = path + dest_name

    try:
        urllib.request.urlretrieve(url, dest)
    except:
        logging.warning("❌Could not download {}".format(url))

    date += timedelta(days=1)
    logging.info("Downloading: {} / {}".format(enddate, date))

# unpack the data and delete the zips afterwards

for (dirpath, dirnames, filenames) in os.walk(path):
    for fileindex, filename in enumerate(filenames):
        if ".tar.gz" in filename:
            # first unzip
            full_filename = path + filename
            with gzip.open(full_filename, 'rb') as f_in:
                with open(full_filename.split(".gz")[0], 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(full_filename)

            # now untar
            with tarfile.open(full_filename.split(".gz")[0], "r") as tar:
                temp_path = full_filename.split(".tar")[0]
                if os.path.isdir(temp_path) == False:
                    os.mkdir(temp_path)
                tarlist = []
                for member in tar.getmembers():
                    tarlist.append(member)
                tar.extractall(temp_path, tarlist)
                tar.close()

            os.remove(full_filename.split(".gz")[0])
            logging.info(
                "Unzipping: {} / {}".format(len(filenames), fileindex+1))

# collecting all the files that need importing in one list
filelist = []
for (dirpath, dirnames, filenames) in os.walk(path):
    for dirname in dirnames:
        dpath = path + "/" + dirname
        for (ddirpath, ddirnames, ffilenames) in os.walk(dpath):
            for ffilename in ffilenames:
                filelist.append(dpath + "/" + ffilename)

# Import into postgresql
# - filter data through the berlin buffer
# - polygonize that data
# - import into radolan_temp
# - join with radolan_geometry and insert into radolan_data
# - purge temporary files

last_received = datetime.strptime("1970-01-01 01:00:00", '%Y-%m-%d %H:%M:%S')

for counter, file in enumerate(filelist):
    input_file = file

    file_split = file.split("/")
    date_time_obj = datetime.strptime(
        file_split[len(file_split)-1], 'RW_%Y%m%d-%H%M.asc')
    if date_time_obj > last_received:
        last_received = date_time_obj
    logging.info("Processing: {} / {}".format(len(filelist), counter+1))

    output_file = path + "temp.tif"

    # clean the temporary folder
    for del_file in [output_file, path + "temp.shp", path + "temp.shx", path + "temp.prj", path + "temp.dbf"]:
        if os.path.exists(del_file):
            os.remove(del_file)

    # for some reason the python gdal bindings are ****. after hours of trying to get this to work in pure python, this has proven to be more reliable and efficient. sorry.

    # filter data
    cmdline = ['gdalwarp', input_file, output_file, "-s_srs", "+proj=stere +lon_0=10.0 +lat_0=90.0 +lat_ts=60.0 +a=6370040 +b=6370040 +units=m", "-t_srs",
               "+proj=stere +lon_0=10.0 +lat_0=90.0 +lat_ts=60.0 +a=6370040 +b=6370040 +units=m", "-r", "near", "-of", "GTiff", "-cutline", "/app/assets/buffer.shp"]
    subprocess.call(cmdline)

    # polygonize data
    cmdline = ['gdal_polygonize.py', output_file, "-f",
               "ESRI Shapefile", path + "temp.shp", "temp", "MYFLD"]
    subprocess.call(cmdline)

    cmdline = None

    df = geopandas.read_file(path + "temp.shp")
    df = df.to_crs("epsg:3857")

    # if there was no rain in Berlin on that timestamp, there will be no data to insert
    if df['geometry'].count() > 0:
        clean = df[(df['MYFLD'] > 0) & (df['MYFLD'].notnull())]
        if len(clean) > 0:
            logging.info("🌧 Found some rain")
            values = []
            for index, row in clean.iterrows():
                values.append(
                    [dumps(row.geometry, rounding_precision=5), row.MYFLD, date_time_obj])
            with conn.cursor() as cur:
                # just to be sure
                cur.execute("DELETE FROM radolan_temp;")
                psycopg2.extras.execute_batch(
                    cur,
                    "INSERT INTO radolan_temp (geometry, value, measured_at) VALUES (ST_Multi(ST_Transform(ST_GeomFromText(%s, 3857), 4326)), %s, %s);",
                    values
                )
                # in order to keep our database fast and small, we are not storing the original polygonized data, but instead we are using a grid and only store the grid ids and the corresponding precipitation data
                cur.execute("INSERT INTO radolan_data (geom_id, value, measured_at) SELECT radolan_geometry.id, radolan_temp.value, radolan_temp.measured_at FROM radolan_geometry JOIN radolan_temp ON ST_WithIn(radolan_geometry.centroid, radolan_temp.geometry);")
                cur.execute("DELETE FROM radolan_temp;")
                conn.commit()
    # memory management, just to be sure
            values = None
        clean = None
    df = None
    date_time_obj = None
    file_split = None
    os.remove(file)
    FNULL = None

# purge data older than 30 days
logging.info("cleaning up old data 🗑️")
timelimit = 30
with conn.cursor() as cur:
    cur.execute(
        "DELETE FROM radolan_data WHERE measured_at < NOW() - INTERVAL '{} days'".format(timelimit))
    conn.commit()


# purge duplicates
logging.info("purging duplicates 🗑️")
with conn.cursor() as cur:
    cur.execute("DELETE FROM radolan_data AS a USING radolan_data AS b WHERE a.id < b.id AND a.geom_id = b.geom_id AND a.measured_at = b.measured_at")
    conn.commit()

# get all grid cells, get data for last 30 days for each grid cell, generate a list for each grid cell
# as we don't store "0" events, those need to be generated, afterwards trees are updated and a geojson is being created

# get the grid and weather data
logging.info("building grid 🌐")
grid = []
with conn.cursor() as cur:
    cur.execute("SELECT radolan_geometry.id, ST_AsGeoJSON(radolan_geometry.geometry), ARRAY_AGG(radolan_data.measured_at) AS measured_at, ARRAY_AGG(radolan_data.value) AS value FROM radolan_geometry JOIN radolan_data ON radolan_geometry.id = radolan_data.geom_id WHERE radolan_data.measured_at > NOW() - INTERVAL '{} days' GROUP BY radolan_geometry.id, radolan_geometry.geometry".format(timelimit))
    grid = cur.fetchall()

# build clean, sorted arrays
clean = []
for cell in grid:
    enddate = datetime.now() + timedelta(days=-1)
    enddate = enddate.replace(hour=23, minute=50, second=0, microsecond=0)
    startdate = datetime.now() + timedelta(days=-timelimit)
    startdate = startdate.replace(hour=0, minute=50, second=0, microsecond=0)
    clean_data = []
    while startdate <= enddate:
        found = False
        for dateindex, date in enumerate(cell[2]):
            if startdate == date:
                found = True
                clean_data.append(cell[3][dateindex])
                # TODO: Add the algorithm that calculates the actually absorbed amount of water (upper & lower threshold)
        if found == False:
            clean_data.append(0)
        startdate += timedelta(hours=1)
    clean.append(clean_data)

# update statistics db
if len(filelist) > 0:
    enddate = datetime.now() + timedelta(days=-1)
    enddate = enddate.replace(hour=23, minute=50, second=0, microsecond=0)
    startdate = datetime.now() + timedelta(days=-timelimit)
    startdate = startdate.replace(hour=0, minute=50, second=0, microsecond=0)
    with conn.cursor() as cur:
        cur.execute("UPDATE radolan_harvester SET collection_date = %s, start_date = %s, end_date = %s WHERE id = 1", [
                    last_received, startdate, enddate])
        conn.commit()

    # update the tree data
    logging.info("updating trees 🌳")
    values = []
    for cellindex, cell in enumerate(grid):
        values.append([clean[cellindex], sum(clean[cellindex]), cell[1]])

    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(
            cur,
            "UPDATE trees SET radolan_days = %s, radolan_sum = %s WHERE ST_CoveredBy(geom, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326));",
            values
        )
        conn.commit()

    # update all the trees we have missed with the first round :(
    logging.info("updating sad trees 🌳")
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(
            cur,
            "UPDATE trees SET radolan_days = %s, radolan_sum = %s WHERE trees.radolan_sum IS NULL AND ST_CoveredBy(geom, ST_Buffer(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 0.00005));",
            values
        )
        conn.commit()

    values = None

    # generate geojson for map and upload to Supabase Storage
    logging.info("generate geojson 🗺️")

    features = []
    features_light = []

    for cellindex, cell in enumerate(grid):
        feature_template = '{{"type":"Feature","geometry":{},"properties":{{"id":{},"data":[{}]}}}}'
        features.append(feature_template.format(
            cell[1], cell[0], ",".join(map(str, clean[cellindex]))))
        features_light.append(feature_template.format(
            cell[1], cell[0], sum(clean[cellindex])))

    def check_file_exists_in_supabase_storage(file_name):
        url = f'{SUPABASE_URL}/storage/v1/object/info/public/{SUPABASE_BUCKET_NAME}/{file_name}'
        response = requests.get(url)
        return response.status_code == 200

    def upload_file_to_supabase_storage(file_path, file_name):
        try:
            file = open(file_path, 'rb')
            file_url = f'{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET_NAME}/{file_name}'
            r = requests.put if check_file_exists_in_supabase_storage(file_name) else requests.post
            response = r(
                file_url,
                files={'file': file},
                headers={
                    'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
                    'ContentType': 'application/geo+json',
                    'AcceptEncoding': 'gzip, deflate, br'
                },
            )

            if response.status_code == 200:
                logging.info("✅ Uploaded {} to supabase storage".format(file_name))
            else:
                logging.warning(response.status_code)
                logging.warning(response.content)
                logging.warning("❌ Could not upload {} to supabase storage".format(file_name))
                
        except Exception as error:
            logging.warning(error)
            logging.warning("❌ Could not upload {} supabase storage".format(file_name))

    def finishGeojson(feature_list, file_name):
        geojson = '{{"type":"FeatureCollection","properties":{{"start":"{}","end":"{}"}},"features":[{}]}}'.format(
            startdate, enddate, ",".join(feature_list))

        text_file = open(path + file_name, "w")
        n = text_file.write(geojson)
        text_file.close()
        n = None

        upload_file_to_supabase_storage(path + file_name, file_name)

    finishGeojson(features, "weather.geojson")
    finishGeojson(features_light, "weather_light.geojson")

    # create a CSV with all trees (id, lat, lng, radolan_sum)
    with conn.cursor() as cur:
        # WARNING: The db is still mislabeled lat <> lng
        cur.execute("SELECT trees.id, trees.lat, trees.lng, trees.radolan_sum, (date_part('year', CURRENT_DATE) - trees.pflanzjahr) as age FROM trees WHERE ST_CONTAINS(ST_SetSRID (( SELECT ST_EXTENT (geometry) FROM radolan_geometry), 4326), trees.geom)")
        trees = cur.fetchall()
        trees_head = "id,lng,lat,radolan_sum,age"
        trees_csv = trees_head
        pLimit = math.ceil(len(trees) / 4)
        pCount = 0
        pfCount = 1
        singleCSV = trees_head
        singleCSVs = []
        for tree in trees:
            newLine = "\n"
            newLine += "{},{},{},{}".format(tree[0], tree[1], tree[2], tree[3])
            if tree[4] is None:
                newLine += ","
            else:
                newLine += ",{}".format(int(tree[4]))
            singleCSV += newLine
            trees_csv += newLine
            pCount += 1
            if pCount >= pLimit:
                text_file = open(path + "trees-p{}.csv".format(pfCount), "w")
                singleCSVs.append(singleCSV)
                n = text_file.write(singleCSV)
                text_file.close()
                n = None
                pfCount += 1
                pCount = 0
                singleCSV = trees_head

        text_file = open(path + "trees-p{}.csv".format(pfCount), "w")
        singleCSVs.append(singleCSV)
        n = text_file.write(singleCSV)
        text_file.close()
        n = None

        text_file = open(path + "trees.csv", "w")
        n = text_file.write(trees_csv)
        text_file.close()
        n = None

        upload_file_to_supabase_storage(path + "trees.csv", "trees.csv")

        for i in range(4):
            upload_file_to_supabase_storage(path + "trees-p{}.csv".format(i + 1), "trees-p{}.csv".format(i + 1))

        # send the updated csv to mapbox

        # get upload credentials
        try:
            url = "https://api.mapbox.com/uploads/v1/{}/credentials?access_token={}".format(
                os.getenv("MAPBOXUSERNAME"), os.getenv("MAPBOXTOKEN"))
            response = requests.post(url)
            s3_credentials = json.loads(response.content)

        # upload latest data

            s3mapbox = boto3.client('s3', aws_access_key_id=s3_credentials["accessKeyId"],
                                    aws_secret_access_key=s3_credentials["secretAccessKey"], aws_session_token=s3_credentials["sessionToken"])
            s3mapbox.upload_file(path + "trees.csv",
                                 s3_credentials["bucket"], s3_credentials["key"])

        # tell mapbox that new data has arrived

            url = "https://api.mapbox.com/uploads/v1/{}?access_token={}".format(
                os.getenv("MAPBOXUSERNAME"), os.getenv("MAPBOXTOKEN"))
            payload = '{{"url":"http://{}.s3.amazonaws.com/{}","tileset":"{}.{}","name":"{}"}}'.format(
                s3_credentials["bucket"], s3_credentials["key"], os.getenv("MAPBOXUSERNAME"), os.getenv("MAPBOXTILESET"), os.getenv("MAPBOXLAYERNAME"))
            headers = {'content-type': 'application/json',
                       'Accept-Charset': 'UTF-8', 'Cache-Control': 'no-cache'}
            response = requests.post(url, data=payload, headers=headers)
            # wohooo!
            logging.info("✅ Map updated to timespan: {} to {}".format(
                startdate, enddate))
        except:
            logging.warning(
                "could not upload tree data to mapbox for vector tiles")
        trees_csv = None
        csv_data = None

    # remove all temporary files
    shutil.rmtree(path)

else:
    logging.info("No updates")

conn.close()
