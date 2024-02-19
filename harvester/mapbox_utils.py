import requests
import json
import time
import boto3
import logging


def upload_to_mapbox_storage(path_to_file, mapbox_username, mapbox_token):
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
    mapbox_storage_credentials, mapbox_username, mapbox_tileset, mapbox_token
):
    url = "https://api.mapbox.com/uploads/v1/{}?access_token={}".format(
        mapbox_username, mapbox_token
    )
    payload = '{{"url":"http://{}.s3.amazonaws.com/{}","tileset":"{}.{}","name":"{}"}}'.format(
        mapbox_storage_credentials["bucket"],
        mapbox_storage_credentials["key"],
        mapbox_username,
        mapbox_tileset,
        mapbox_token,
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
    complete = False
    error = None
    while not complete and error is None:
        logging.info(
            f"Waiting for tileset creation for upload={tileset_generation_id} progress={progress} complete={complete} error={error}"
        )
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
        time.sleep(2)
