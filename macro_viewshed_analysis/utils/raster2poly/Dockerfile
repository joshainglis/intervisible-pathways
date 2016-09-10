FROM gliderlabs/alpine:3.4
MAINTAINER Josha Inglis <joshainglis@gmail.com>

VOLUME /in
VOLUME /out

WORKDIR /code

RUN apk --update add \
    ca-certificates \
    gdal \
    geos \
    openssl \
    py-pip \
    py-numpy \
    python \
    --update-cache \
    --repository http://dl-3.alpinelinux.org/alpine/edge/community/ --allow-untrusted \
    --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ --allow-untrusted

RUN apk --update add --virtual build-dependencies \
        python-dev \
        build-base \
        gdal-dev \
        geos-dev \
        py-numpy-dev \
        --update-cache \
        --repository http://dl-3.alpinelinux.org/alpine/edge/community/ --allow-untrusted \
        --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ --allow-untrusted \
    && pip install \
        fiona \
        rasterio \
        shapely \
    && apk del build-dependencies

COPY ./disaggregate_viewsheds.py /code

ENV VIEWSHEDS_PER_FILE=32
ENV OVERFLOW=31

ENTRYPOINT ["/usr/bin/python", "/code/disaggregate_viewsheds.py"]
