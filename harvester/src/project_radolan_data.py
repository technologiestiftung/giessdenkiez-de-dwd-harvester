import os
import subprocess


# Resources:
# https://proj.org/en/9.2/usage/quickstart.html
# https://brightsky.dev/docs/#/operations/getRadar
# https://gdal.org/programs/gdalwarp.html
# https://www.ogc.org/standard/geotiff/
def project_radolan_data(hourly_radolan_file, shape_file, root_dir):
    """Projects the given radolan data to Mercator, cuts out the area of interest by using a shape file.

    Args:
        hourly_radolan_file (str): Path to the hourly radolan file
        shape_file (str): Path to the shape file defining the area of interest
        root_dir (str): Path to the directory holding the temp files

    Returns:
        str: Path to the generated GeoTIFF file
    """
    output_file = os.path.join(root_dir, hourly_radolan_file.split("/")[-1] + ".tiff")
    cmdline = [
        "gdalwarp",
        hourly_radolan_file,
        output_file,
        "-s_srs",
        "+proj=stere +lon_0=10.0 +lat_0=90.0 +lat_ts=60.0 +a=6370040 +b=6370040 +units=m",
        "-t_srs",
        "+proj=stere +lon_0=10.0 +lat_0=90.0 +lat_ts=60.0 +a=6370040 +b=6370040 +units=m",
        "-r",
        "near",
        "-of",
        "GTiff",
        "-cutline",
        shape_file,
    ]
    subprocess.call(cmdline, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return output_file


# Resources:
# https://gdal.org/programs/gdal_polygonize.html
# https://www.esri.com/content/dam/esrisites/sitecore-archive/Files/Pdfs/library/whitepapers/pdfs/shapefile.pdf
def polygonize_data(input_raster_file, root_dir):
    """Produces a polygon feature layer from a raster as an ESRI Shapefile

    Args:
        input_raster_file (str): Path to input raster file
        root_dir (str): Path to the directory holding the temp files

    Returns:
        str: Path to generated ESRI Shapefile
    """
    output_file = os.path.join(root_dir, input_raster_file.split("/")[-1] + ".shp")
    cmdline = [
        "gdal_polygonize.py",
        input_raster_file,
        "-f",
        "ESRI Shapefile",
        output_file,
        "RDLLAYER",
        "RDLFIELD",
    ]
    subprocess.call(cmdline, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return output_file
