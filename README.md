![](https://img.shields.io/badge/Built%20with%20%E2%9D%A4%EF%B8%8F-at%20Technologiestiftung%20Berlin-blue)

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->

[![All Contributors](https://img.shields.io/badge/all_contributors-7-orange.svg?style=flat-square)](#contributors-)

<!-- ALL-CONTRIBUTORS-BADGE:END -->

# giessdenkiez-de-dwd-harvester

- Gather precipitation data from DWD's radolan data set, for the region of Berlin and connect to the giessdenkiez.de postgres DB
- Uploads trees combined with weather data to Mapbox and uses its API to create vector tiles for use on mobile devices
- Generates CSV and GeoJSON files that contain trees locations and weather data (grid) and uploads them to a Supabase Storage bucket
- Fetch historical weather data via BrightSky API: https://brightsky.dev/ 

## Development environment

It is recommended to use Python virtual environments to manage and separate Python dependencies:

```
python -m venv REPO_DIRECTORY
```

## Install dependencies

```
pip install -r requirements.txt
```

or (if you are on MacOS)

```
pip install -r requirements-mac.txt
```

### Dependency troubleshooting

- If installing `psycopg2` on MacOS fails, there nmight be a problem with the ssl-lib linking. Following install resolved the issue:
```
env LDFLAGS='-L/usr/local/lib -L/usr/local/opt/openssl/lib -L/usr/local/opt/readline/lib' pip install psycopg2
```

- The project uses the command line tool of GDAL (because the Python bindings are hard to install without dependency conflicts). The GDAL dependency is not listed in the requirements file and must therefore be installed manually on the system: For Mac, use `brew install gdal`: https://formulae.brew.sh/formula/gdal For Linux, follow https://mothergeo-py.readthedocs.io/en/latest/development/how-to/gdal-ubuntu-pkg.html 

### Configuration

Copy the `sample.env` file and rename to `.env` then update all variables:

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
WEATHER_HARVEST_LAT=52.520008
WEATHER_HARVEST_LNG=13.404954
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

### 4. Harvesting daily weather data
For harvesting daily weather data, we use the free and open source [BrightSky API](https://brightsky.dev/docs/#/). No API key is needed. The script is defined in [run_daily_weather.py](harvester/src/run_daily_weather.py).
Make sure to set all relevant environment variables before running the script, e.g. for a run with local database attached:

```
PG_SERVER=localhost
PG_PORT=54322
PG_USER=postgres
PG_DB=postgres
PG_PASS=postgres
WEATHER_HARVEST_LAT=52.520008
WEATHER_HARVEST_LNG=13.404954
```

Make sure that especially `WEATHER_HARVEST_LAT` and `WEATHER_HARVEST_LNG` are set to your destination of interest.

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
