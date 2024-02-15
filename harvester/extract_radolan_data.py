import geopandas
from shapely.wkt import dumps


# Resources:
# https://epsg.io/3857
def extract_radolan_data_from_shapefile(
    polygonized_shape_file, measured_at_timestamp, root_dir
):
    radolan_field_key = "RDLFIELD"
    df = geopandas.read_file(polygonized_shape_file)
    df = df.to_crs("epsg:3857")
    values = []
    if df["geometry"].count() > 0:
        radolan_data = df[
            (df[radolan_field_key] > 0) & (df[radolan_field_key].notnull())
        ]
        if len(radolan_data) > 0:
            for _, row in radolan_data.iterrows():
                values.append(
                    [
                        dumps(row.geometry, rounding_precision=5),
                        row[radolan_field_key],
                        measured_at_timestamp,
                    ]
                )
    return values
