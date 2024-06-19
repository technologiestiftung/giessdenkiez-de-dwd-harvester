import sys
import psycopg2.extras
import psycopg2
from dotenv import load_dotenv
import logging
import os
import requests
import datetime

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
]:
    if env_var not in os.environ:
        logging.error("❌Environmental Variable {} does not exist".format(env_var))
        sys.exit(1)

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

today = datetime.date.today()

# Calculate the date one year ago
one_year_ago = today - datetime.timedelta(days=365)

# Generate a list of all dates between one year ago and today
date_list = [
    one_year_ago + datetime.timedelta(days=x)
    for x in range((today - one_year_ago).days + 1)
]

for date in date_list:
    full_day = date
    url = "https://api.brightsky.dev/weather"
    params = {
        "date": full_day,
        "lat": 52.520008,
        "lon": 13.404954,
    }
    headers = {"Accept": "application/json"}
    response = requests.get(url, params=params, headers=headers)
    weather_raw = response.json()
    weather = weather_raw["weather"]
    interesting_weather = [
        {"precipitation": x["precipitation"], "temperature": x["temperature"]}
        for x in weather
    ]
    precipitation_sum_mm_per_sqm = sum(
        [x["precipitation"] for x in interesting_weather]
    )
    temperature_avg = sum([x["temperature"] for x in interesting_weather]) / len(
        interesting_weather
    )
    with database_connection.cursor() as cur:
        cur.execute(
            "INSERT INTO weather_data (date, avg_temperature_celsius, precipitation_sum_mm_per_sqm) VALUES (%s, %s, %s)",
            [full_day, temperature_avg, precipitation_sum_mm_per_sqm],
        )
    database_connection.commit()
    print(full_day, temperature_avg, precipitation_sum_mm_per_sqm)
