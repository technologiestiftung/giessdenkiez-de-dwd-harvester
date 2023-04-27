# building a buffer shape for filtering the weather data
import os
import geopandas
from shapely.ops import unary_union
from dotenv import load_dotenv

INPUT_PATH_DEFAULT = "./assets/Berlin.shp"
INPUT_BUFFER_DEFAULT = 2000

load_dotenv()

input_path = os.getenv("INPUT_SHAPEFILE", INPUT_PATH_DEFAULT)
input_buffer = os.getenv("INPUT_SHAPEFILE_BUFFER", INPUT_BUFFER_DEFAULT)

input = geopandas.read_file(input_path)
input = input.to_crs("epsg:3857")
input_boundary = geopandas.GeoDataFrame(geopandas.GeoSeries(unary_union(input['geometry'])))
input_boundary = input_boundary.rename(columns={0:'geometry'}).set_geometry('geometry')

output = input_boundary.buffer(int(input_buffer))
output = output.simplify(1000)

output = geopandas.GeoDataFrame(output)
output = output.rename(columns={0:'geometry'}).set_geometry('geometry')
output.crs = "epsg:3857"
output.to_file("./assets/buffer.shp")
