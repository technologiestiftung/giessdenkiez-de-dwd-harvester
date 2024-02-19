import geopandas
from shapely.wkt import dumps


# Resources:
# https://epsg.io/3857
# https://doc.arcgis.com/en/arcgis-online/reference/shapefiles.htm
def extract_radolan_data_from_shapefile(polygonized_shape_file, measured_at_timestamp):
    """Extract radolon values from given shapefile

    Args:
        polygonized_shape_file (_type_): the shapefile data should be extracted from
        measured_at_timestamp (_type_): the timestamp of the extraction

    Returns:
        _type_: list of extracted radolon data for each cell in the shapefile
    """
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
