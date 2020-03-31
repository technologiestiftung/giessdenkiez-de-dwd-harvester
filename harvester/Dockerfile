# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.8.1-slim-buster



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
WORKDIR /app
# Install pip requirements
COPY requirements.txt /app
RUN python -m pip install -r requirements.txt
COPY . /app

# During debugging, this entry point will be overridden. For more information, refer to https://aka.ms/vscode-docker-python-debug
ENTRYPOINT ["python", "harvester.py"]
