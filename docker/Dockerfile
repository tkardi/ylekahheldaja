FROM osgeo/gdal:ubuntu-small-latest

WORKDIR /main

ENV PYTHONPATH=/main

COPY ./main .

RUN \
    useradd gdaluser -s /usr/sbin/nologin -u 1022 -m \
    && mkdir /data \
    && chown gdaluser:gdaluser -R /data \
    && chown gdaluser:gdaluser -R /main

USER gdaluser

ENTRYPOINT [ "python3", "/main/app/ylekahheldus.py" ]
