# building a buffer shape for filtering the weather data
import geopandas
from shapely.ops import cascaded_union

def create_buffer_shape(shape_file, buffer_distance = 2000):
    shape = geopandas.read_file(shape_file)
    shape = shape.to_crs("epsg:3857")
    boundary = geopandas.GeoDataFrame(geopandas.GeoSeries(cascaded_union(shape['geometry'])))
    boundary = boundary.rename(columns={0:'geometry'}).set_geometry('geometry')

    buffer = boundary.buffer(buffer_distance)
    buffer = buffer.simplify(1000)

    buffer = geopandas.GeoDataFrame(buffer)
    buffer = buffer.rename(columns={0:'geometry'}).set_geometry('geometry')
    buffer.crs = "epsg:3857"

    return buffer

buffer = create_buffer_shape('./assets/Berlin.shp')
buffer.to_file("./assets/buffer.shp")
