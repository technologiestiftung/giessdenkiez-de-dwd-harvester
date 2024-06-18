from shapely import wkt
from shapely.geometry import Polygon
from pyproj import Proj, transform
from functools import partial
from shapely.ops import transform as shapely_transform

# Define the WKT polygon
wkt_polygon = "POLYGON((13.49710961030364 52.65437623435893,13.50423666410478 52.65411202062176,13.50336520844766 52.64547732806005,13.48913251668174 52.64600493717479,13.49000023534728 52.65463871905796,13.49710961030364 52.65437623435893))"

# Convert WKT to a Shapely geometry
polygon = wkt.loads(wkt_polygon)

# Define the projection for the original coordinates (WGS 84)
proj_wgs84 = Proj(init="epsg:4326")

# Define an equal-area projection (e.g., EPSG:6933, World Cylindrical Equal Area)
proj_equal_area = Proj(init="epsg:6933")

# Function to transform coordinates using pyproj transform
transformer = partial(transform, proj_wgs84, proj_equal_area)

# Transform the polygon coordinates to the equal-area projection
polygon_projected = shapely_transform(transformer, polygon)

# Calculate the area in square meters
area_sq_m = polygon_projected.area

# Convert the area to square kilometers
area_sq_km = area_sq_m / 1e6

print(f"Area: {area_sq_km} km²")
