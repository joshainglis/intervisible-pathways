FROM fedora:24

RUN dnf -y upgrade
RUN dnf -y install python-devel geos-devel python-numpy gcc gcc-c++ redhat-rpm-config gdal-devel

RUN pip install --upgrade pip
RUN pip install shapely rasterio fiona jupyter

CMD ["/usr/bin/jupyter-notebook", "--no-browser"]

