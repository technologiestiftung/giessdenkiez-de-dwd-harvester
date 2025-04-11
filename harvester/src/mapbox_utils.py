import requests
import json
import time
import boto3
import logging
import psycopg2
from datetime import datetime
from datetime import timedelta
import pytz


def upload_to_mapbox_storage(path_to_file, mapbox_username, mapbox_token):
    """Uploads the given file to a Mapbox storage

    Args:
        path_to_file (str): the full path to the file to upload
        mapbox_username (str): the Mapbox username
        mapbox_token (str): the Mapbox token

    Returns:
        _type_: Mabox credentials dictionary holding bucket and key information
    """
    logging.info(f"Uploading data to Mapbox storage...")
    url = "https://api.mapbox.com/uploads/v1/{}/credentials?access_token={}".format(
        mapbox_username, mapbox_token
    )
    response = requests.post(url)
    mapbox_storage_credentials = json.loads(response.content)

    s3mapbox = boto3.client(
        "s3",
        aws_access_key_id=mapbox_storage_credentials["accessKeyId"],
        aws_secret_access_key=mapbox_storage_credentials["secretAccessKey"],
        aws_session_token=mapbox_storage_credentials["sessionToken"],
    )

    s3mapbox.upload_file(
        path_to_file,
        mapbox_storage_credentials["bucket"],
        mapbox_storage_credentials["key"],
    )

    return mapbox_storage_credentials


def start_tileset_creation(
    mapbox_storage_credentials,
    mapbox_username,
    mapbox_tileset,
    mapbox_layer_name,
    mapbox_token,
):
    """Start the Mapbox tileset creation

    Args:
        path_tomapbox_storage_credentials_file (dict): dictionary holding bucket and key of the data
        mapbox_username (str): the Mapbox username
        mapbox_tileset (str): the Mapbox tileset name
        mapbox_token (str): the Mapbox token

    Returns:
        str: Mapbox upload id of the started tileset creation
    """
    logging.info(f"Starting Mapbox tileset creation...")
    url = "https://api.mapbox.com/uploads/v1/{}?access_token={}".format(
        mapbox_username, mapbox_token
    )
    payload = '{{"url":"http://{}.s3.amazonaws.com/{}","tileset":"{}.{}","name":"{}"}}'.format(
        mapbox_storage_credentials["bucket"],
        mapbox_storage_credentials["key"],
        mapbox_username,
        mapbox_tileset,
        mapbox_layer_name,
    )
    headers = {
        "content-type": "application/json",
        "Accept-Charset": "UTF-8",
        "Cache-Control": "no-cache",
    }
    response = requests.post(url, data=payload, headers=headers)
    if response.status_code != 201:
        logging.error("Could not start Mapbox tileset creation")
        logging.error(response.content)

    upload_id = json.loads(response.content)["id"]

    return upload_id


def wait_for_tileset_creation_complete(
    tileset_generation_id, mapbox_username, mapbox_token
):
    """Checks progress of the Mapbox tileset creation profcess

    Args:
        tileset_generation_id (str): the ID of the started Mapbox tileset creation
        mapbox_username (str): the Mapbox username
        mapbox_token (str): the Mapbox token

    Returns:
        error: None, if no error occurred
    """
    complete = False
    error = None
    while not complete and error is None:
        url = "https://api.mapbox.com/uploads/v1/{}/{}?access_token={}".format(
            mapbox_username,
            tileset_generation_id,
            mapbox_token,
        )
        headers = {
            "content-type": "application/json",
            "Accept-Charset": "UTF-8",
            "Cache-Control": "no-cache",
        }
        response = requests.get(url, headers=headers)
        responseJson = json.loads(response.content)
        complete = responseJson["complete"]
        error = responseJson["error"]
        progress = responseJson["progress"]
        logging.info(
            f"Waiting for tileset creation for upload={tileset_generation_id} progress={progress} complete={complete} error={error}"
        )
        time.sleep(2)

    return error


def update_trees_in_database(radolan_grid, db_conn):
    """Updates tree radolon data in database

    Args:
        radolan_grid (_type_): the radolon value grid to use for updating the trees
        db_conn (_type_): the database connection
    """
    logging.info(f"Updating trees in database...")

    # First update block: Process iteratively
    updated_count1 = 0
    try:
        with db_conn.cursor() as cur:
            sql = """
                UPDATE trees
                SET radolan_days = %s, radolan_sum = %s
                WHERE ST_CoveredBy(geom, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326));
            """
            for item in radolan_grid:
                try:
                    cur.execute(sql, item)
                    updated_count1 += cur.rowcount
                except Exception as e:
                    logging.error(f"Error updating item {item}: {e}")
                    # Optionally rollback or decide how to handle partial failures
                    # db_conn.rollback() might be too coarse here.
            db_conn.commit() # Commit after processing all items in the first loop
            logging.info(f"First update block affected {updated_count1} rows.")
    except Exception as e:
        logging.error(f"Error during first update block: {e}")
        db_conn.rollback() # Rollback if the loop itself fails badly
        raise # Re-raise the exception

    # Second update block: Process iteratively (similar change needed)
    updated_count2 = 0
    try:
        with db_conn.cursor() as cur:
             sql_buffer = """
                 UPDATE trees
                 SET radolan_days = %s, radolan_sum = %s
                 WHERE trees.radolan_sum IS NULL
                 AND ST_CoveredBy(geom, ST_Buffer(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 0.0002));
             """
             for item in radolan_grid:
                 try:
                     cur.execute(sql_buffer, item)
                     updated_count2 += cur.rowcount
                 except Exception as e:
                     logging.error(f"Error updating buffered item {item}: {e}")
             db_conn.commit() # Commit after processing all items in the second loop
             logging.info(f"Second update block affected {updated_count2} rows.")
    except Exception as e:
        logging.error(f"Error during second update block: {e}")
        db_conn.rollback()
        raise
