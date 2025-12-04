FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    GDAL_CONFIG=/usr/bin/gdal-config \
    CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal

# Set environment variables for LocalTileServer
ENV LOCALTILESERVER_CLIENT_PREFIX='proxy/{port}'

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      gdal-bin libgdal-dev \
      libgeos-dev libproj-dev \
      libpq-dev && \
    rm -rf /var/lib/apt/lists/* \

WORKDIR /app

COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8503

ENTRYPOINT ["streamlit","run","main.py","--server.address=0.0.0.0","--server.port=8503"]