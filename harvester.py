# loading the environmental variables
from dotenv import load_dotenv
load_dotenv()

# make environmental variables accessible
import os
# SECRET_KEY = os.getenv("EMAIL")

# database connection
import psycopg2
import psycopg2.extras

pg_server = os.getenv("PG_SERVER")
pg_port = os.getenv("PG_PORT")
pg_username = os.getenv("PG_USER")
pg_password = os.getenv("PG_PASS")
pg_database = os.getenv("PG_DB")

dsn = f"host='{pg_server}' port={pg_port} user='{pg_username}' password='{pg_password}' dbname='{pg_database}'"

# nice console output / turn console output off in .env
import sys
def consoleOutput (str):
  if os.getenv("OUTPUT") == True or os.getenv("OUTPUT") == "True" :
    sys.stdout.write("\033[K")
    print(str, end="\r")

# get last day of insert
last_date = None
with psycopg2.connect(dsn) as conn:
  with conn.cursor() as cur:
    cur.execute("SELECT collection_date FROM radolan_harvester WHERE id = 1")
    last_date = cur.fetchone()[0]

# create a temporary folder to store the downloaded DWD data
path = "./temp/"
if os.path.isdir(path) != True:
  os.mkdir(path)

# now download all zips starting from last date, until yesterday (DWD usually uploads the latest data at some point during the night)
from datetime import datetime  
from datetime import timedelta
import urllib.request

enddate = datetime.now() + timedelta(days=-1)
date = datetime.combine(last_date, datetime.min.time()) + timedelta(days=1)

while date <= enddate:
  url = 'https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/radolan/recent/asc/RW-{}.tar.gz'.format(date.strftime("%Y%m%d"))
  url_split = url.split("/")
  dest_name = url_split[len(url_split) - 1]
  dest = path + dest_name
  urllib.request.urlretrieve(url, dest)
  date += timedelta(days=1)
  consoleOutput("Downloading: {} / {}".format(enddate, date))

# unpack the data and delete the zips afterwards
import tarfile
import gzip
import shutil

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
      consoleOutput("Unzipping: {} / {}".format(len(filenames), fileindex+1))

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
import subprocess
from shapely.wkt import dumps
import geopandas

last_received = datetime.strptime("1970-01-01 01:00:00", '%Y-%m-%d %H:%M:%S')

for counter, file in enumerate(filelist):
  input_file = file
  FNULL = open(os.devnull, 'w')
    
  file_split = file.split("/")
  date_time_obj = datetime.strptime(file_split[len(file_split)-1], 'RW_%Y%m%d-%H%M.asc')
  if date_time_obj > last_received:
    last_received = date_time_obj
  consoleOutput("Processing: {} / {}".format(len(filelist), counter+1))

  output_file = path + "temp.tif"

  # clean the temporary folder
  for del_file in [output_file, path + "temp.shp", path + "temp.shx", path + "temp.prj", path + "temp.dbf"]:
    if os.path.exists(del_file):
      os.remove(del_file)

  # for some reason the python gdal bindings are ****. after hours of trying to get this to work in pure python, this has proven to be more reliable and efficient. sorry.

  # filter data
  cmdline = ['gdalwarp', input_file, output_file, "-s_srs", "+proj=stere +lon_0=10.0 +lat_0=90.0 +lat_ts=60.0 +a=6370040 +b=6370040 +units=m", "-t_srs", "+proj=stere +lon_0=10.0 +lat_0=90.0 +lat_ts=60.0 +a=6370040 +b=6370040 +units=m", "-r", "near", "-of", "GTiff", "-cutline", "./assets/buffer.shp" ]
  # if you want debugging info, remove the last to params
  subprocess.call(cmdline, stdout=FNULL, stderr=subprocess.STDOUT)

  # polygonize data
  cmdline = ['gdal_polygonize.py', output_file, "-f", "ESRI Shapefile", path + "temp.shp", "temp", "MYFLD"]
  # if you want debugging info, remove the last to params
  subprocess.call(cmdline, stdout=FNULL, stderr=subprocess.STDOUT)
    
  cmdline = None

  df = geopandas.read_file(path + "temp.shp")
  df = df.to_crs("epsg:3857")

  # if there was no rain in Berlin on that timestamp, there will be no data to insert
  if df['geometry'].count() > 0:
    clean = df[(df['MYFLD'] > 0) & (df['MYFLD'].notnull())]
    if len(clean) > 0:
      values = []
      for index, row in clean.iterrows():
        values.append([dumps(row.geometry, rounding_precision=5), row.MYFLD, date_time_obj])
      with psycopg2.connect(dsn) as conn:
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
  # memory management, just to be sure
      values = None
    clean = None
  df = None
  date_time_obj = None
  file_split = None
  os.remove(file)
  FNULL = None

# purge data older than 30 days
consoleOutput("cleaning up old data 🗑️")
timelimit = 30
with psycopg2.connect(dsn) as conn:
  with conn.cursor() as cur:
    cur.execute("DELETE FROM radolan_data WHERE measured_at < NOW() - INTERVAL '{} days'".format(timelimit))

# purge duplicates
with psycopg2.connect(dsn) as conn:
  with conn.cursor() as cur:
    cur.execute("DELETE FROM radolan_data AS a USING radolan_data AS b WHERE a.id < b.id AND a.geom_id = b.geom_id AND a.measured_at = b.measured_at")

# get all grid cells, get data for last 30 days for each grid cell, generate a list for each grid cell
# as we don't store "0" events, those need to be generated, afterwards trees are updated and a geojson is being created

# get the grid and weather data
consoleOutput("building grid 🌐")
grid = []
with psycopg2.connect(dsn) as conn:
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
enddate = datetime.now() + timedelta(days=-1)
enddate = enddate.replace(hour=23, minute=50, second=0, microsecond=0)
startdate = datetime.now() + timedelta(days=-timelimit)
startdate = startdate.replace(hour=0, minute=50, second=0, microsecond=0)
with psycopg2.connect(dsn) as conn:
  with conn.cursor() as cur:
    cur.execute("UPDATE radolan_harvester SET collection_date = %s, start_date = %s, end_date = %s WHERE id = 1", [last_received, startdate, enddate])

# update the tree data
consoleOutput("updating trees 🌳")
values = []
for cellindex, cell in enumerate(grid):
  values.append([clean[cellindex], sum(clean[cellindex]), cell[1]])

with psycopg2.connect(dsn) as conn:
  with conn.cursor() as cur:
    psycopg2.extras.execute_batch(
        cur,
        "UPDATE trees SET radolan_days = %s, radolan_sum = %s WHERE ST_CoveredBy(geom, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326));",
        values
    )
values = None

# generate gejson for map and upload to S3
consoleOutput("generate geojson 🗺️")
import boto3
s3 = boto3.client('s3', aws_access_key_id=os.getenv("ACCESS_KEY"), aws_secret_access_key=os.getenv("SECRET_KEY"))

features = []
features_light = []

for cellindex, cell in enumerate(grid):
  feature_template = '{{"type":"Feature","geometry":{},"properties":{{"id":{},"data":[{}]}}}}'
  features.append(feature_template.format(cell[1], cell[0], ",".join(map(str, clean[cellindex]))))
  features_light.append(feature_template.format(cell[1], cell[0], sum(clean[cellindex])))

def finishGeojson (feature_list, file_name):
  geojson = '{{"type":"FeatureCollection","properties":{{"start":{},"end":{}}}"features":[{}]}}'.format(startdate, enddate, ",".join(feature_list))

  text_file = open(path + file_name, "w")
  n = text_file.write(geojson)
  text_file.close()
  n = None

  s3.upload_file(path + file_name, os.getenv("S3_BUCKET"), file_name)

finishGeojson(features, "weather.geojson")
finishGeojson(features_light, "weather_light.geojson")

# remove all temporary files
shutil.rmtree(path)

# wohooo!
sys.stdout.write("\033[K")
print("✅ Map updated to timespan: {} to {}".format(startdate, enddate))