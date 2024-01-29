import os
import requests
import json
import tempfile
import time
import shutil
import subprocess
import boto3
from datetime import datetime
import psycopg2
import logging
from tqdm import tqdm

def uploadAndRegenerateLayer(absolute_file_path, mapboxUsername, tilesetId, tilesetLayerName):
    # Get credentials
    url = "https://api.mapbox.com/uploads/v1/{}/credentials?access_token={}".format(
        os.getenv("MAPBOXUSERNAME"), os.getenv("MAPBOXTOKEN")
    )
    response = requests.post(url)
    s3_credentials = json.loads(response.content)

    s3mapbox = boto3.client(
        "s3",
        aws_access_key_id=s3_credentials["accessKeyId"],
        aws_secret_access_key=s3_credentials["secretAccessKey"],
        aws_session_token=s3_credentials["sessionToken"],
    )


    # Upload the latest tree data to S3
    s3mapbox.upload_file(
        absolute_file_path,
        s3_credentials["bucket"],
        s3_credentials["key"],
    )

    # Tell Mapbox that new data has arrived for trees
    url = "https://api.mapbox.com/uploads/v1/{}?access_token={}".format(
        os.getenv("MAPBOXUSERNAME"), os.getenv("MAPBOXTOKEN")
    )
    payload = '{{"url":"http://{}.s3.amazonaws.com/{}","tileset":"{}.{}","name":"{}"}}'.format(
        s3_credentials["bucket"],
        s3_credentials["key"],
        mapboxUsername,
        tilesetId,
        tilesetLayerName,
    )
    headers = {
        "content-type": "application/json",
        "Accept-Charset": "UTF-8",
        "Cache-Control": "no-cache",
    }
    response = requests.post(url, data=payload, headers=headers)
    if response.status_code != 201:
        logging.error("Could not generate Mapbox upload")
        logging.error(response.content)

    upload_id = json.loads(response.content)["id"]
    logging.info(
        f"Initialized generation of Mapbox tilesets for upload={upload_id}..."
    )

    # Check for the status of Mapbox upload until completed or error
    complete = False
    error = None
    while not complete and error is None:
        url = "https://api.mapbox.com/uploads/v1/{}/{}?access_token={}".format(
            os.getenv("MAPBOXUSERNAME"), upload_id, os.getenv("MAPBOXTOKEN")
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
            f"Waiting for tileset generation for upload={upload_id} progress={progress} complete={complete} error={error}"
        )
        time.sleep(2)

    if error is not None:
        logging.error(error)
        exit(1)