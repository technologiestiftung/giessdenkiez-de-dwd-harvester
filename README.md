![](https://img.shields.io/badge/Built%20with%20%E2%9D%A4%EF%B8%8F-at%20Technologiestiftung%20Berlin-blue)

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->

[![All Contributors](https://img.shields.io/badge/all_contributors-7-orange.svg?style=flat-square)](#contributors-)

<!-- ALL-CONTRIBUTORS-BADGE:END -->

# giessdenkiez-de-dwd-harvester

- Gather precipitation data from DWD's radolan data set, for the region of Berlin and connect to the giessdenkiez.de postgres DB
- Uploads trees combined with weather data to Mapbox and uses its API to create vector tiles for use on mobile devices
- Generates CSV and GeoJSON files that contain trees locations and weather data (grid) and uploads them to a Supabase Storage bucket

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

### GDAL

As some of python's gdal bindings are not as good as the command line tool, i had to use the original. Therefore, `gdal` needs to be installed. GDAL is a dependency in requirements.txt, but sometimes this does not work. Then GDAL needs to be installed manually. Afterwards, make sure the command line calls for `gdalwarp` and `gdal_polygonize.py` are working.

#### Linux

Here is a good explanation on how to install gdal on linux: https://mothergeo-py.readthedocs.io/en/latest/development/how-to/gdal-ubuntu-pkg.html

#### Mac

For mac we can use `brew install gdal`.

The current python binding of gdal is fixed to GDAL==2.4.2. If you get another gdal (`ogrinfo --version`), make sure to upgrade to your version: `pip install GDAL==VERSION_FROM_PREVIOUS_COMMAND`

### Configuration

Copy the `sample.env` file and rename to `.env` then update the parameters, most importantly the database connection parameters.

```
PG_SERVER=localhost
PG_PORT=54322
PG_USER=postgres
PG_PASS=postsgres
PG_DB=postgres
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_ROLE=eyJh...
SUPABASE_BUCKET_NAME=data_assets
MAPBOXUSERNAME=your_mapbox_username
MAPBOXTOKEN=your_mapbox
MAPBOXTILESET=your_mapbox_tileset_id
MAPBOXLAYERNAME=your_mapbox_layer_name
SKIP_MAPBOX=False
LIMIT_DAYS=30
SURROUNDING_SHAPE_FILE=./assets/buffer.shp
```

## Running

Starting from an empty database, the complete process of running the DWD harvester consists of three steps:

1. Preparing the buffered shapefile
2. Creating the grid structure for the `radolan_geometry` table
3. Harvesting the DWD data

### 1. Preparing the buffered shapefile

Firstly, a buffered shapefile is needed, which is created with the following commands. This step is utilizing the `harvester/assets/berlin.prj` and `harvester/assets/berlin.shp` files. Make sure to set the environment variables properly before running this step.

- `cd harvester/prepare`
- `SHAPE_RESTORE_SHX=YES python create-buffer.py`

### 2. Creating the grid structure for the `radolan_geometry` table

Secondly, the `radolan_geometry` table needs to be populated. You need to have the buffered shapefile (from the previous step) created and available in `../assets`. The `radolan_geometry` table contains vector data for the target city. The data is needed by the harvest process to find the rain data for the target city area. This repository contains shape files for Berlin area. To make use of it for another city, replace the `harvester/assets/berlin.prj` and `harvester/assets/berlin.shp` files. Run the following commands to create the grid structure in the database:

- `cd harvester/prepare`
- `python create-grid.py`

### 3. Harvesting the DWD data

Make sure to set the environment variables properly before running the script. Make sure that you have succesfully ran the previous steps for preparing the buffered shapefile and creating the grid structure for the `radolan_geometry` table. The file `harvester/src/run_harvester.py` contains the script for running the DWD harvester, it does the following:

- Checks for existens of all required environment variables
- Setup database connection
- Get start end end date of current harvesting run (for incremental harvesting every day)
- Download all daily radolan files from DWD server
- Extracts the daily radolan files into hourly radolan files
- For each hourly radolan file:
  - Projects the given data to Mercator, cuts out the area of interest. Using `gdalwarp` library.
  - Produce a polygon feature layer. Using `gdal_polygonize.py` library.
  - Extract raw radolan values from generate feature layer.
  - Upload extracted radolan values to database
- Cleanup old radolan values in database (keep only last 30 days)
- Build a radolan grid holding the hourly radolan values for the last 30 days for each polygon in the grid.
- Updates `radolan_sum` and `radolan_values` columns in the database `trees` table
- Updates the Mapbox trees layer:
  - Build a trees.csv file based on all trees (with updated radolan values) in the database
  - Preprocess trees.csv using `tippecanoe` library.
  - Start the creation of updated Mapbox layer

## Docker

To have a local database for testing you need Docker and docker-compose installed. You will also have to create a public Supabase Storage bucket. You also need to update the `.env` file with the values from `sample.env` below the line `# for your docker environment`.

to start only the database run

```bash
docker-compose -f  docker-compose.postgres.yml up
```

This will setup a postgres/postgis DB and provision the needed tables and insert some test data.

To run the harvester and the postgres db run

```bash
docker-compose up
```

### Known Problems

#### harvester.py throws Error on first run

When running the setup for the first time `docker-compose up` the provisioning of the database is slower then the execution of the harvester container. You will have to stop the setup and run it again to get the desired results.

#### Postgres Provisioning

The provisioning `sql` script is only run once when the container is created. When you create changes you will have to run:

```bash
docker-compose down
docker-compose up --build

```

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://fabianmoronzirfas.me/"><img src="https://avatars.githubusercontent.com/u/315106?v=4?s=64" width="64px;" alt="Fabian Morón Zirfas"/><br /><sub><b>Fabian Morón Zirfas</b></sub></a><br /><a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/commits?author=ff6347" title="Code">💻</a> <a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/commits?author=ff6347" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://www.sebastianmeier.eu/"><img src="https://avatars.githubusercontent.com/u/302789?v=4?s=64" width="64px;" alt="Sebastian Meier"/><br /><sub><b>Sebastian Meier</b></sub></a><br /><a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/commits?author=sebastian-meier" title="Code">💻</a> <a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/commits?author=sebastian-meier" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dnsos"><img src="https://avatars.githubusercontent.com/u/15640196?v=4?s=64" width="64px;" alt="Dennis Ostendorf"/><br /><sub><b>Dennis Ostendorf</b></sub></a><br /><a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/commits?author=dnsos" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Lisa-Stubert"><img src="https://avatars.githubusercontent.com/u/61182572?v=4?s=64" width="64px;" alt="Lisa-Stubert"/><br /><sub><b>Lisa-Stubert</b></sub></a><br /><a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/commits?author=Lisa-Stubert" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/vogelino"><img src="https://avatars.githubusercontent.com/u/2759340?v=4?s=64" width="64px;" alt="Lucas Vogel"/><br /><sub><b>Lucas Vogel</b></sub></a><br /><a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/commits?author=vogelino" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/JensWinter"><img src="https://avatars.githubusercontent.com/u/6548550?v=4?s=64" width="64px;" alt="Jens Winter-Hübenthal"/><br /><sub><b>Jens Winter-Hübenthal</b></sub></a><br /><a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/commits?author=JensWinter" title="Code">💻</a> <a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/issues?q=author%3AJensWinter" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://simonjockers.de"><img src="https://avatars.githubusercontent.com/u/449739?v=4?s=64" width="64px;" alt="Simon Jockers"/><br /><sub><b>Simon Jockers</b></sub></a><br /><a href="#infra-sjockers" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/commits?author=sjockers" title="Code">💻</a> <a href="https://github.com/technologiestiftung/giessdenkiez-de-dwd-harvester/issues?q=author%3Asjockers" title="Bug reports">🐛</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

## Credits

<table>
  <tr>
    <td>
      <a src="https://citylab-berlin.org/en/start/">
        <br />
        <br />
        <img width="200" src="https://logos.citylab-berlin.org/logo-citylab-berlin.svg" />
      </a>
    </td>
    <td>
      A project by: <a src="https://www.technologiestiftung-berlin.de/en/">
        <br />
        <br />
        <img width="150" src="https://logos.citylab-berlin.org/logo-technologiestiftung-berlin-en.svg" />
      </a>
    </td>
    <td>
      Supported by:
      <br />
      <br />
      <img width="120" src="https://logos.citylab-berlin.org/logo-berlin.svg" />
    </td>
  </tr>
</table>
