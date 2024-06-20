#!/bin/sh
set -e

python ./src/run_daily_weather.py || {
    echo "run_daily_weather.py failed";
    exit 1;
}

python ./src/run_harvester.py || {
    echo "run_harvester.py failed";
    exit 1;
}