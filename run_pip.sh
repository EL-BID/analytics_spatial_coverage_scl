#!/bin/bash

sudo yum -y update
sudo yum-config-manager --enable epel
sudo yum -y install make automake gcc gcc-c++ libcurl-devel proj-devel geos-devel
cd /tmp
curl -L http://download.osgeo.org/gdal/2.0.0/gdal-2.0.0.tar.gz | tar zxf -
cd gdal-2.0.0/
./configure --prefix=/usr/local --without-python
make -j4
sudo make install
cd /usr/local
tar zcvf ~/gdal-2.0.0-amz1.tar.gz *

#conda env create -f environment.yml
#conda init bash
#conda activate geopandas
sudo pip install -r requirements.txt