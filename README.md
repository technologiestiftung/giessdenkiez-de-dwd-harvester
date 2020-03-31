# dwd-radolan-tree-harvester
Gather precipitation data from DWD's radolan data set, for the region of Berlin and connect to the trees DB

## Pre-Install

I am using venv to setup a virtual python environment for separating dependencies:
```
python -m venv REPO_DIRECTORY
```

## Install
```
pip install -r requirements.txt
```

I had some trouble installing psycopg2 on MacOS, there is a problem with the ssl-lib linking. Following install resolved the issue:

```
env LDFLAGS='-L/usr/local/lib -L/usr/local/opt/openssl/lib -L/usr/local/opt/readline/lib' pip install psycopg2
```

As some of python's gdal bindings are not as good as the command line tool, i had to use the original. Therefore, `gdal` needs to be installed.

Make sure the command line calls for `gdalwarp` and `gdal_polygonize.py` are working.

Here is a good explanation on how to install gdal on linux: https://mothergeo-py.readthedocs.io/en/latest/development/how-to/gdal-ubuntu-pkg.html

For mac we can use `brew install gdal`.

The current python binding of gdal is fixed to GDAL==2.4.2. If you get another gdal (`ogrinfo --version`), make sure to upgrade to your version: `pip install GDAL==VERSION_FROM_PREVIOUS_COMMAND`

Copy the `sample.env` file and rename to `.env` then update the parameters, most importantly the database connection parameters.

## Running

`prepare.py` shows how the assets/buffer.shp was created. If a bigger buffer is needed change `line 10` accordingly and re-run.

`harvester.py` is the actual file for harvesting the data. Simply run, no command line parameters, all settings are in `.env`.

The code in `harvester.py` tries to clean up after running the code. But, when running this in a container, as the script is completely stand alone, its probably best to just destroy the whole thing and start from scratch next time.