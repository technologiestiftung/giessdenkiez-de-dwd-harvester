import requests
import json
import time
import boto3
import logging


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
