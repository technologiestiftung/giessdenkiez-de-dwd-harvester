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
    """Preprocesses the given trees.csv file with tippecanoe to fulfill the requirements from Mapbox
       to create a tileset

    Args:
        trees_csv_full_path (str): the full path to the trees.csv
        temp_dir (str): the full path to the directory to store the preprocessed file

    Returns:
        str: full path to the preprocessed trees file
    """
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
    """Generate a trees.csv file containing all trees currently in the databae

    Args:
        temp_dir (str): the full path to the directory to store the preprocessed file
        db_conn: the database connection

    Returns:
        str: full path to the trees.csv file
    """
    logging.info(f"Generating trees.csv...")
    current_year = datetime.now().year
    with db_conn.cursor() as cur:

        # Fetch all trees from database
        cur.execute(
            # WARNING: The coordinates in the database columns lat and lng are mislabeled! They mean the opposite.
            """
                SELECT
                    trees.id,
                    ST_Y(geom) AS lat,
                    ST_X(geom) AS lng,
                    trees.radolan_sum,
                    trees.pflanzjahr,
                    COALESCE(SUM(w.amount), 0) AS watering_sum
                FROM
                    trees
                LEFT JOIN
                    trees_watered w ON w.tree_id = trees.id AND w.timestamp >= CURRENT_DATE - INTERVAL '30 days' AND DATE_TRUNC('day', w.timestamp) < CURRENT_DATE
                WHERE
                    ST_CONTAINS(ST_SetSRID ((SELECT ST_EXTENT (geometry) FROM radolan_geometry), 4326), trees.geom)
                GROUP BY
                    trees.id, trees.lat, trees.lng, trees.radolan_sum, trees.pflanzjahr;
            """
        )
        trees = cur.fetchall()

        # Get all waterings that are included in the amount of waterings for the last 30 days
        cur.execute(
            """
                SELECT * FROM trees_watered w WHERE w.timestamp >= CURRENT_DATE - INTERVAL '30 days' AND DATE_TRUNC('day', w.timestamp) < CURRENT_DATE;
            """
        )
        trees_watered = cur.fetchall()

        logging.info(f"Creating trees.csv file for {len(trees)} trees...")

        # Build CSV file with all trees in it
        header = "id,lat,lng,radolan_sum,age,watering_sum,total_water_sum_liters"
        lines = []
        for tree in tqdm(trees):
            id = tree[0]
            lat = tree[1]
            lng = tree[2]

            # precipitation height in 0.1 mm per square meter
            # 1mm on a square meter is 1 liter
            # e.g. value of 380 = 0.1 * 380 = 38.0 mm * 1 liter = 38 liters
            radolan_sum = float(tree[3]) if tree[3] != None else 0

            # Age is undefined ("" for Mapbox) if pflanzjahr is None or 0
            pflanzjahr = tree[4]
            age = (
                ""
                if (pflanzjahr == None or pflanzjahr == 0)
                else int(current_year) - int(pflanzjahr)
            )

            # total_water_sum_liters calculated in liters to be easily usable in the frontend
            watering_sum = float(tree[5])
            total_water_sum_liters = (radolan_sum / 10.0) + watering_sum

            line = f"{id}, {lat}, {lng}, {radolan_sum}, {age}, {watering_sum}, {total_water_sum_liters}"
            lines.append(line)
        trees_csv = "\n".join([header] + lines)
        trees_csv_full_path = os.path.join(temp_dir, "trees.csv")
        with open(trees_csv_full_path, "w") as out:
            out.write(trees_csv)

        return (trees_csv_full_path, trees_watered)


def update_mapbox_tree_layer(
    mapbox_username,
    mapbox_token,
    mapbox_tileset,
    mapbox_layer_name,
    supabase_url,
    supabase_bucket_name,
    supabase_service_role_key,
    db_conn,
):

    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate trees.csv from trees in database
        (trees_csv_full_path, trees_watered) = generate_trees_csv(temp_dir, db_conn)

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
            mapbox_layer_name,
            mapbox_token,
        )

        tileset_creation_error = wait_for_tileset_creation_complete(
            tileset_generation_id,
            mapbox_username,
            mapbox_token,
        )

        if tileset_creation_error is not None:
            logging.error("Could not create Mapbox tileset")

        return trees_watered


def update_tree_waterings(trees_watered, db_conn):
    print(f"Set included_in_map_layer = TRUE for {len(trees_watered)} watered trees...")
    tree_ids = [tree_watered[4] for tree_watered in trees_watered]
    with db_conn.cursor() as cur:
        # Set included_in_map_layer = FALSE for all waterings
        cur.execute(
            """
                UPDATE trees_watered SET included_in_map_layer = FALSE WHERE TRUE;
            """,
            (tree_ids,),
        )
        db_conn.commit()

        # Set included_in_map_layer = FALSE for the waterings that are included in this round of the harvester
        cur.execute(
            """
                UPDATE trees_watered SET included_in_map_layer = TRUE WHERE id = ANY (%s);
            """,
            (tree_ids,),
        )
        db_conn.commit()
