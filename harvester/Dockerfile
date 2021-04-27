# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.8.1-slim-buster as base

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

RUN apt-get update \
  && apt-get install g++ gdal-bin libgdal-dev libpq-dev -y \
  && rm -rf /var/lib/apt/lists/*
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
# RUN pip install GDAL

FROM base as builder


# Install pip requirements
COPY requirements.txt /app/
RUN cd /app/ && python -m pip install --no-warn-script-location --prefix=/install -r requirements.txt

FROM base as app
COPY --from=builder /install /usr/local

# COPY harvester.py /app/
# COPY prepare.py /app/
# COPY grid/ grid/
# COPY assets/ /app/assets
COPY . /app/


CMD ["python", "/app/harvester.py"]
