# building a buffer shape for filtering the weather data
import geopandas
import geopandas.testing
from shapely.ops import cascaded_union
from prepare import create_buffer_shape
import subprocess
import os

def test_create_buffer_with_default_distance():
    buffer = create_buffer_shape('./assets/test/shape.shp')

    expected_buffer_2000 = geopandas.read_file(f"./assets/test/buffer_2000.shp")
    expected_buffer_2000.drop("FID", inplace=True, axis=1)

    geopandas.testing.assert_geodataframe_equal(buffer, expected_buffer_2000)

def test_create_buffer_with_custom_distance():
    buffer_1000 = create_buffer_shape('./assets/test/shape.shp', 1000)

    expected_buffer_1000 = geopandas.read_file(f"./assets/test/buffer_1000.shp")
    expected_buffer_1000.drop("FID", inplace=True, axis=1)

    geopandas.testing.assert_geodataframe_equal(buffer_1000, expected_buffer_1000)

def test_buffer_file_gets_created():
    subprocess.run(["python", "prepare.py"])
    assert os.path.exists("./assets/buffer.shp")
