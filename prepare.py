# building a buffer shape for filtering the weather data
import geopandas
from shapely.ops import cascaded_union

berlin = geopandas.read_file("./assets/Berlin.shp")
berlin = berlin.to_crs("epsg:3857")
berlin_boundary = geopandas.GeoDataFrame(geopandas.GeoSeries(cascaded_union(berlin['geometry'])))
berlin_boundary = berlin_boundary.rename(columns={0:'geometry'}).set_geometry('geometry')

berlin_buffer = berlin_boundary.buffer(2000)
berlin_buffer = berlin_buffer.simplify(1000)

berlin_buffer = geopandas.GeoDataFrame(berlin_buffer)
berlin_buffer = berlin_buffer.rename(columns={0:'geometry'}).set_geometry('geometry')
berlin_buffer.crs = "epsg:3857"
berlin_buffer.to_file("./assets/buffer.shp")