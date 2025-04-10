import os
import subprocess
import logging


# Resources:
# https://proj.org/en/9.2/usage/quickstart.html
# https://brightsky.dev/docs/#/operations/getRadar
# https://gdal.org/programs/gdalwarp.html
# https://www.ogc.org/standard/geotiff/
def project_radolan_data(hourly_radolan_file, shape_file, tmp_dir):
    """Projects the given Radolan to Mercator, cuts out the area of interest by using a shape file.
    Args:
        hourly_radolan_file (str): Path to the hourly radolan file
        shape_file (str): Path to the shape file defining the area of interest
        tmp_dir (str): Path to the directory holding the temp files
    Returns:
        str: Path to the generated GeoTIFF file
    Raises:
        RuntimeError: If gdalwarp fails.
        FileNotFoundError: If input files are missing.
    """
    logging.info(f"Projecting radolan data for {hourly_radolan_file}...")

    # Check inputs
    if not os.path.exists(hourly_radolan_file):
        logging.error(f"Input radolan file not found: {hourly_radolan_file}")
        raise FileNotFoundError(f"Input radolan file not found: {hourly_radolan_file}")
    if not os.path.exists(shape_file):
        logging.error(f"Input shape file not found: {shape_file}")
        raise FileNotFoundError(f"Input shape file not found: {shape_file}")

    output_file = os.path.join(tmp_dir, os.path.basename(hourly_radolan_file) + ".tiff")

    # Note: The source and target SRS are identical here. Is this intentional?
    # It might be redundant unless gdalwarp is needed for other options like -cutline.
    # Consider if simple file copying or linking is sufficient if no projection change or clipping is needed.
    cmdline = [
        "gdalwarp",
        hourly_radolan_file,
        output_file,
        "-s_srs", # Source SRS
        "+proj=stere +lon_0=10.0 +lat_0=90.0 +lat_ts=60.0 +a=6370040 +b=6370040 +units=m",
        "-t_srs", # Target SRS
        "+proj=stere +lon_0=10.0 +lat_0=90.0 +lat_ts=60.0 +a=6370040 +b=6370040 +units=m",
        "-r",     # Resampling method
        "near",
        "-of",    # Output format
        "GTiff",
        "-cutline", # Cutline dataset
        shape_file,
        # Consider adding "-crop_to_cutline" if you only want the area inside the shapefile
        # Consider adding "-overwrite" if you might rerun and want to replace existing files
    ]

    try:
        result = subprocess.run(
            cmdline,
            check=False,
            capture_output=True,
            text=True
        )

        if result.stdout:
            logging.debug(f"gdalwarp stdout:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"gdalwarp stderr:\n{result.stderr}")

        if result.returncode != 0:
            logging.error(f"gdalwarp failed with exit code {result.returncode}")
            raise RuntimeError(f"gdalwarp failed. Stderr: {result.stderr}")

        if not os.path.exists(output_file):
             logging.error(f"gdalwarp ran but output tiff not found: {output_file}")
             raise FileNotFoundError(f"Output tiff missing after gdalwarp: {output_file}")

        logging.info(f"Successfully created projected tiff: {output_file}")
        return output_file

    except FileNotFoundError as e:
        logging.error(f"Failed to run gdalwarp. Is GDAL installed and in PATH? Error: {e}")
        raise RuntimeError("gdalwarp command not found. Check GDAL installation.") from e
    except Exception as e:
        logging.error(f"An unexpected error occurred during projection: {e}")
        raise


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
    Raises:
        RuntimeError: If gdal_polygonize.py fails.
    """
    logging.info(f"Polygonize radolan data for {input_raster_file}...")
    # Ensure the input file exists before trying to process
    if not os.path.exists(input_raster_file):
        logging.error(f"Input raster file not found: {input_raster_file}")
        raise FileNotFoundError(f"Input raster file not found: {input_raster_file}")

    # Construct output path (shapefile requires companion files, GDAL handles this)
    base_name = os.path.basename(input_raster_file)
    output_shapefile = os.path.join(root_dir, base_name + ".shp")

    cmdline = [
        "gdal_polygonize.py",
        input_raster_file,
        "-f",
        "ESRI Shapefile",
        output_shapefile,
        "RDLLAYER", # Layer name in the shapefile
        "RDLFIELD", # Field name for the raster values
    ]

    try:
        # Use subprocess.run to capture output and check return code
        result = subprocess.run(
            cmdline,
            check=False, # Don't automatically raise error on non-zero exit
            capture_output=True, # Capture stdout and stderr
            text=True # Decode stdout/stderr as text
        )

        # Log stdout/stderr for debugging regardless of success/failure
        if result.stdout:
            logging.debug(f"gdal_polygonize stdout:\n{result.stdout}")
        if result.stderr:
            # Log stderr as warning even if successful, as GDAL sometimes prints info there
            logging.warning(f"gdal_polygonize stderr:\n{result.stderr}")

        # Check if the command failed
        if result.returncode != 0:
            logging.error(f"gdal_polygonize.py failed with exit code {result.returncode}")
            raise RuntimeError(f"gdal_polygonize.py failed. Stderr: {result.stderr}")

        # Verify the primary output file (.shp) was created
        if not os.path.exists(output_shapefile):
             logging.error(f"gdal_polygonize.py ran but output shapefile not found: {output_shapefile}")
             raise FileNotFoundError(f"Output shapefile missing after gdal_polygonize: {output_shapefile}")

        logging.info(f"Successfully created shapefile: {output_shapefile}")
        return output_shapefile

    except FileNotFoundError as e:
        # Handle case where gdal_polygonize.py itself isn't found
        logging.error(f"Failed to run gdal_polygonize.py. Is GDAL installed and in PATH? Error: {e}")
        raise RuntimeError("gdal_polygonize.py command not found. Check GDAL installation.") from e
    except Exception as e:
        logging.error(f"An unexpected error occurred during polygonization: {e}")
        raise # Re-raise other unexpected errors
