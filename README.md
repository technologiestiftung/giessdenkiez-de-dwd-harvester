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

Copy the `sample.env` file and rename to `.env` then update the parameters, most importantly the database connection parameters.

## Running

`prepare.py` shows how the assets/buffer.shp was created. If a bigger buffer is needed change `line 10` accordingly and re-run.

`harvester.py` is the actual file for harvesting the data. Simply run, no command line parameters, all settings are in `.env`.

The code in `harvester.py` tries to clean up after running the code. But, when running this in a container, as the script is completely stand alone, its probably best to just destroy the whole thing and start from scratch next time.