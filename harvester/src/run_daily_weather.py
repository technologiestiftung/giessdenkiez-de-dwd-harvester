import sys
import psycopg2.extras
import psycopg2
from dotenv import load_dotenv
import logging
import os
import requests
import datetime

# This script fetches hourly weather data from the BrightSky API, aggregates it to daily weather data and stores it in the database

# Set up logging
logging.basicConfig()
logging.root.setLevel(logging.INFO)

# Load the environmental variables
load_dotenv()

# Check if all required environmental variables are accessible
for env_var in [
    "PG_SERVER",
    "PG_PORT",
    "PG_USER",
    "PG_PASS",
    "PG_DB",
    "WEATHER_HARVEST_LAT",
    "WEATHER_HARVEST_LNG",
]:
    if env_var not in os.environ:
        logging.error("❌Environmental Variable {} does not exist".format(env_var))
        sys.exit(1)

PG_SERVER = os.getenv("PG_SERVER")
PG_PORT = os.getenv("PG_PORT")
PG_USER = os.getenv("PG_USER")
PG_PASS = os.getenv("PG_PASS")
PG_DB = os.getenv("PG_DB")
WEATHER_HARVEST_LAT = os.getenv("WEATHER_HARVEST_LAT")
WEATHER_HARVEST_LNG = os.getenv("WEATHER_HARVEST_LNG")

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


def extract(weather_list, field):
    return [
        data_point[field]
        for data_point in weather_list
        if data_point[field] is not None
    ]


print(f"📅 Fetching weather data for {len(date_list)} days...")
weather_days_in_db = []
with database_connection.cursor() as cur:
    cur.execute("SELECT measure_day, day_finished FROM daily_weather_data;")
    weather_days_in_db = cur.fetchall()

for date in date_list:
    today = datetime.date.today()
    full_day = date

    existing_weather_in_db_for_this_day = [
        data_point_in_db
        for data_point_in_db in weather_days_in_db
        if data_point_in_db[0].date() == full_day
    ]
    if existing_weather_in_db_for_this_day != []:
        logging.info(f"🌦 Weather data for {full_day} already exists in the database...")
        if existing_weather_in_db_for_this_day[0][1] == False:
            logging.info(
                f"🌦 Weather data for {full_day} was not finished in last run, updating now..."
            )
            with database_connection.cursor() as cur:
                cur.execute(
                    "DELETE FROM daily_weather_data WHERE measure_day = %s", [today]
                )
            database_connection.commit()
        else:
            continue

    # Using BrightSky API to fetch weather data https://brightsky.dev/docs/#/
    # Hint: No API key is required
    url = "https://api.brightsky.dev/weather"
    params = {
        "date": full_day,
        "lat": WEATHER_HARVEST_LAT,
        "lon": WEATHER_HARVEST_LNG,
    }
    headers = {"Accept": "application/json"}
    response = requests.get(url, params=params, headers=headers)
    weather_raw = response.json()
    weather = weather_raw["weather"]

    # Aggregate hourly weather data to daily weather data
    sum_precipitation_mm_per_sqm = sum(extract(weather, "precipitation"))
    avg_temperature_celsius = sum(extract(weather, "temperature")) / len(weather)
    avg_pressure_msl = sum(extract(weather, "pressure_msl")) / len(weather)
    sum_sunshine_minutes = sum(extract(weather, "sunshine"))
    avg_wind_direction_deg = sum(extract(weather, "wind_direction")) / len(weather)
    avg_wind_speed_kmh = sum(extract(weather, "wind_speed")) / len(weather)
    avg_cloud_cover_percentage = sum(extract(weather, "cloud_cover")) / len(weather)
    avg_dew_point_celcius = sum(extract(weather, "dew_point")) / len(weather)
    avg_relative_humidity_percentage = sum(extract(weather, "relative_humidity")) / len(
        weather
    )
    avg_visibility_m = sum(extract(weather, "visibility")) / len(weather)
    avg_wind_gust_direction_deg = sum(extract(weather, "wind_gust_direction")) / len(
        weather
    )
    avg_wind_gust_speed_kmh = sum(extract(weather, "wind_gust_speed")) / len(weather)

    source_dwd_station_ids = extract(weather_raw["sources"], "dwd_station_id")

    day_finished = full_day < today

    logging.info(f"🌦 Weather data for {full_day} fetched via BrightySky API...")

    with database_connection.cursor() as cur:
        cur.execute(
            "INSERT INTO daily_weather_data (measure_day, day_finished, sum_precipitation_mm_per_sqm, avg_temperature_celsius, avg_pressure_msl, sum_sunshine_minutes, avg_wind_direction_deg, avg_wind_speed_kmh, avg_cloud_cover_percentage, avg_dew_point_celcius, avg_relative_humidity_percentage, avg_visibility_m, avg_wind_gust_direction_deg, avg_wind_gust_speed_kmh, source_dwd_station_ids) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                full_day,
                day_finished,
                sum_precipitation_mm_per_sqm,
                avg_temperature_celsius,
                avg_pressure_msl,
                sum_sunshine_minutes,
                avg_wind_direction_deg,
                avg_wind_speed_kmh,
                avg_cloud_cover_percentage,
                avg_dew_point_celcius,
                avg_relative_humidity_percentage,
                avg_visibility_m,
                avg_wind_gust_direction_deg,
                avg_wind_gust_speed_kmh,
                source_dwd_station_ids,
            ],
        )
    database_connection.commit()
