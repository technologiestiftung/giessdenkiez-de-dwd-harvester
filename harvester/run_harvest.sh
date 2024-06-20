#!/bin/sh
set -e

python ./src/run_daily_weather.py || {
    echo "run_daily_weather.py failed"
    FAILED=1
}

python ./src/run_harvester.py || {
    echo "run_harvester.py failed"
    FAILED=1
}

if [ "$FAILED" = "1" ]; then
    exit 1
fi