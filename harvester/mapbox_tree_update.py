import os
import tempfile
import subprocess
from datetime import datetime
import logging
from tqdm import tqdm
from mapbox_utils import (
    upload_to_mapbox_storage,
    start_tileset_creation,
    wait_for_tileset_creation_complete,
)
from supabase_utils import upload_file_to_supabase_storage


def preprocess_trees_csv(trees_csv_full_path, temp_dir):
    logging.info("Preprocessing trees.csv with tippecanoe...")
    trees_preprocessed_full_path = os.path.join(temp_dir, "trees-preprocessed.mbtiles")
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
    return trees_preprocessed_full_path


def generate_trees_csv(temp_dir, db_conn):
    logging.info(f"Creatinging trees.csv file for {len(trees)} trees...")
    current_year = datetime.now().year
    with db_conn.cursor() as cur:

        # Fetch all trees from database
        cur.execute(
            # WARNING: The coordinates in the database columns lat and lng are mislabeled! They mean the opposite.
            """
            SELECT
                trees.id,
                trees.lat,
                trees.lng,
                trees.radolan_sum,
                trees.pflanzjahr
            FROM
                trees
            WHERE
                ST_CONTAINS(ST_SetSRID ((
                        SELECT
                            ST_EXTENT (geometry)
                            FROM radolan_geometry), 4326), trees.geom)
            """
        )
        trees = cur.fetchall()

        # Build CSV file with all trees in it
        header = "id,lng,lat,radolan_sum,age"
        lines = []
        for tree in tqdm(trees):
            age = int(current_year) - int(tree[4]) if tree[4] != 0 else ""
            line = "{},{},{},{},{}".format(tree[0], tree[1], tree[2], tree[3], age)
            lines.append(line)
        trees_csv = "\n".join([header] + lines)
        trees_csv_full_path = os.path.join(temp_dir, "trees.csv")
        with open(trees_csv_full_path, "w") as out:
            out.write(trees_csv)

        return trees_csv_full_path


def update_mapbox_tree_layer(
    mapbox_username,
    mapbox_token,
    mapbox_tileset,
    supabase_url,
    supabase_bucket_name,
    supabase_service_role_key,
    db_conn,
):

    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate trees.csv from trees in database
        trees_csv_full_path = generate_trees_csv(temp_dir, db_conn)

        # Preprocess trees.csv with tippecanoe
        trees_preprocessed_full_path = preprocess_trees_csv(
            trees_csv_full_path, temp_dir
        )

        # Upload preprocessed trees to Supabase storage
        upload_file_to_supabase_storage(
            supabase_url,
            supabase_bucket_name,
            supabase_service_role_key,
            trees_preprocessed_full_path,
            "trees-preprocessed.mbtiles",
        )

        # Start the Mapbox tileset creating
        mapbox_storage_credentials = upload_to_mapbox_storage(
            trees_preprocessed_full_path,
            mapbox_username,
            mapbox_token,
        )

        tileset_generation_id = start_tileset_creation(
            mapbox_storage_credentials,
            mapbox_username,
            mapbox_tileset,
            mapbox_token,
        )

        tileset_creation_error = wait_for_tileset_creation_complete(
            tileset_generation_id,
            mapbox_username,
            mapbox_token,
        )

        if tileset_creation_error is not None:
            logging.error("Could not create Mapbox tileset")
