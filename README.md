# ylekahheldaja
`ylekahheldaja` aitab olemasolevast `TMS` teenusest uusi (muu suurus, teine
bbox) tile'e kirjutada. Kasutab
[osgeo/gdal:ubuntu-small-latest](https://hub.docker.com/r/osgeo/gdal) docker
_image_ 'it, muu loogika sama _image_ 'i Pythonis (3.10)

## config
- [src/main/resources/server/ma-kaart.xml](src/main/resources/server/ma-kaart.xml)
on `GDAL` `TMS` kihi konfiguratsioon. Hetkel ainuke, aga põhimõtteliselt võimalik
juurde lisada teisi ja parameteriseerida "teenuse nimi".
- [src/main/resources/zooms/](src/main/resources/zooms/) on kahhlipõhine
konfiguratsioon. Need on csv failid iga _zoom_ i-põhiselt (nimi kujul `<zoom>.csv`).
Selle struktuur:

| veerg | kirjeldus |
|-------|-----------|
| dir | Ebaoluline, ei kasuta kuskil, kuid csv vaates "hea teada" :) |
| minx | Tile'i `minx` koordinaat. Eeldatud on `EPSG:3301`, x idasuunaline |
| maxy | Tile'i `maxy` koordinaat. Eeldatud on `EPSG:3301`, x idasuunaline |
| maxx | Tile'i `maxx` koordinaat. Eeldatud on `EPSG:3301`, x idasuunaline |
| miny | Tile'i `miny` koordinaat. Eeldatud on `EPSG:3301`, x idasuunaline |
| width | Tile'i laius/kõrgus px. [00.csv](src/main/resources/zooms/00.csv) puhul 1024, [01.csv](src/main/resources/zooms/01.csv) 2048, kõik ülejäänud 4096 |
| x | Tile'i x väärtus |
| y | Tile'i y väärtus |

Failinimi moodustatakse kui `<zoom>`/`<x>_<y>.tiff`. Kõigile tiff failidele
ehitatakse püramiidid (3 levelit) ja genereeritakse _tiff-world-file_ (`*.twf`).

csv-failide genereerimiseks (alates `z>2`) saab kasutada järgmist
PostgreSQL/PostGIS SQL päringut:

```
with
    bounds as (
        select
            301187.0 as minx, 6754812.0 as maxy,
            813187.0 as maxx, 6242812.0 as miny
    ),
    f as (
        select p as z, pow(2, p)::int as div
        from generate_series(1,12) p
    )
select
    lpad((z+2)::varchar,2, '0') as dir,
    minx, maxy, maxx, miny,
    4096 as width,
    x, y
from (
    select
        f.z, x, y, f.div,
        round(bounds.minx+((bounds.maxx-bounds.minx)/div::numeric)::numeric*x::numeric,1) as minx,
        round(bounds.miny+((bounds.maxy-bounds.miny)/div::numeric)::numeric*(y+1)::numeric,1) as maxy,
        round(bounds.minx+((bounds.maxx-bounds.minx)/div::numeric)::numeric*(x+1)::numeric,1) as maxx,
        round(bounds.miny+((bounds.maxy-bounds.miny)/div::numeric)::numeric*y::numeric,1) as miny
    from
        bounds,
        f
            left join generate_series(0, f.div-1) x on true
            left join generate_series(0, f.div-1) y on true
    ) r
        join lateral
            st_envelope(
                st_makeline(
                    st_point(minx, maxy, 3301), st_point(maxx,miny, 3301)
                )
            ) env on true
    where
        exists (
            select 1
            from ay_subs a
            where st_intersects(a.geom, env)
    )
```

kus `ay_subs` on
[Maa-ameti kodulehelt](https://geoportaal.maaamet.ee/est/Ruumiandmed/Haldus-ja-asustusjaotus-p119.html)
andmebaasi laetud ja eeltöödeldud asustusüksuste andmestik. Selle eeltöötlemine:

```
drop table if exists ay_subs;
create table ay_subs as
select
    st_subdivide((st_dump(geom)).geom, 256) as geom
from ay;

alter table ay_subs add column oid serial;
alter table ay_subs add constraint pk__ay_subs primary key (oid);

create index sidx__ay_subs on ay_subs using gist (geom);
```


## Building

```
~/repos/ylekahheldus$ source build.sh
Sending build context to Docker daemon  4.031MB
Step 1/7 : FROM osgeo/gdal:ubuntu-small-latest
 ---> aa266c4177c0
Step 2/7 : WORKDIR /main
 ---> Using cache
 ---> f5b0b24c40cd
Step 3/7 : ENV PYTHONPATH=/main
 ---> Using cache
 ---> 7468d8abbf54
Step 4/7 : COPY ./main .
 ---> 9af8cecd474b
Step 5/7 : RUN     useradd gdaluser -s /usr/sbin/nologin -u 1022 -m     && mkdir /data     && chown gdaluser:gdaluser -R /data     && chown gdaluser:gdaluser -R /main
 ---> Running in 724aea889e4d
Removing intermediate container 724aea889e4d
 ---> 02b5b3ffe3cd
Step 6/7 : USER gdaluser
 ---> Running in 8165d3a83580
Removing intermediate container 8165d3a83580
 ---> 87deabbef4b1
Step 7/7 : ENTRYPOINT [ "python3", "/main/app/ylekahheldus.py" ]
 ---> Running in d7e557520439
Removing intermediate container d7e557520439
 ---> 3c656bbf4ae0
Successfully built 3c656bbf4ae0
Successfully tagged localhost/ylekahheldus:latest
~/repos/ylekahheldus$
```

## cli help

```
~/repos/ylekahheldus$ docker run --rm -it --name ylekahheldus localhost/ylekahheldus:latest --help
usage: /main/app/ylekahheldus.py [-h] [-m MINZOOM] [-x MAXZOOM] [-l LOGLEVEL]

options:
  -h, --help            show this help message and exit
  -m MINZOOM, --minzoom MINZOOM
                        minzoom value. Defaults to 0
  -x MAXZOOM, --maxzoom MAXZOOM
                        maxzoom value. Defaults to 11
  -l LOGLEVEL, --loglevel LOGLEVEL
                        Log level. Defaults to INFO
~/repos/ylekahheldus$
```

## Running
Rada taili-failide salvestamiseks kohalikus masinas:

```
~/repos/ylekahheldus$ mkdir test
~/repos/ylekahheldus$ chmod -R 0777 test/
```

_Ex 1_: Lae alla zoomid 0, 1, 2 kasutades loglevel DEBUG eelloodud rajale `./test`
```
~/repos/ylekahheldus$ docker run --rm -it -v $PWD/test:/data --name ylekahheldus localhost/ylekahheldus:latest --minzoom 0 --maxzoom 2 --loglevel DEBUG
2022-12-19 11:53:05,098; INFO; ZOOM 00 from /main/app/../resources/zooms/00.csv
2022-12-19 11:53:05,098; INFO; Path /data/00 does not exist. Creating...
2022-12-19 11:53:05,098; DEBUG; Saving tiles to /data/00
2022-12-19 11:53:05,099; DEBUG; gdal_translate -co COMPRESS=LZW -co TILED=YES -co TFW=YES -projwin_srs EPSG:3301 -projwin 301187.0 6754812.0 813187.0 6242812.0 -outsize 1024 1024 /main/app/../resources/server/ma-kaart.xml /data/00/0_0.tiff
2022-12-19 11:53:05,961; DEBUG; Input file size is 4194304, 4194304
2022-12-19 11:53:05,961; DEBUG; 0...10...20...30...40...50...60...70...80...90...100 - done.
2022-12-19 11:53:05,961; DEBUG;
2022-12-19 11:53:05,961; DEBUG; gdaladdo /data/00/0_0.tiff 3
2022-12-19 11:53:06,004; DEBUG; 0...10...20...30...40...50...60...70...80...90...100 - done.
2022-12-19 11:53:06,004; DEBUG;
2022-12-19 11:53:06,004; INFO; ZOOM 01 from /main/app/../resources/zooms/01.csv
2022-12-19 11:53:06,004; INFO; Path /data/01 does not exist. Creating...
2022-12-19 11:53:06,004; DEBUG; Saving tiles to /data/01
2022-12-19 11:53:06,004; DEBUG; gdal_translate -co COMPRESS=LZW -co TILED=YES -co TFW=YES -projwin_srs EPSG:3301 -projwin 301187.0 6754812.0 813187.0 6242812.0 -outsize 2048 2048 /main/app/../resources/server/ma-kaart.xml /data/01/0_0.tiff
2022-12-19 11:53:07,836; DEBUG; Input file size is 4194304, 4194304
2022-12-19 11:53:07,837; DEBUG; 0...10...20...30...40...50...60...70...80...90...100 - done.
2022-12-19 11:53:07,837; DEBUG;
2022-12-19 11:53:07,837; DEBUG; gdaladdo /data/01/0_0.tiff 3
2022-12-19 11:53:07,928; DEBUG; 0...10...20...30...40...50...60...70...80...90...100 - done.
2022-12-19 11:53:07,929; DEBUG;
2022-12-19 11:53:07,929; INFO; ZOOM 02 from /main/app/../resources/zooms/02.csv
2022-12-19 11:53:07,929; INFO; Path /data/02 does not exist. Creating...
2022-12-19 11:53:07,929; DEBUG; Saving tiles to /data/02
2022-12-19 11:53:07,929; DEBUG; gdal_translate -co COMPRESS=LZW -co TILED=YES -co TFW=YES -projwin_srs EPSG:3301 -projwin 301187.0 6754812.0 813187.0 6242812.0 -outsize 4096 4096 /main/app/../resources/server/ma-kaart.xml /data/02/0_0.tiff
2022-12-19 11:53:13,529; DEBUG; Input file size is 4194304, 4194304
2022-12-19 11:53:13,530; DEBUG; 0...10...20...30...40...50...60...70...80...90...100 - done.
2022-12-19 11:53:13,530; DEBUG;
2022-12-19 11:53:13,530; DEBUG; gdaladdo /data/02/0_0.tiff 3
2022-12-19 11:53:13,788; DEBUG; 0...10...20...30...40...50...60...70...80...90...100 - done.
2022-12-19 11:53:13,788; DEBUG;
~/repos/ylekahheldus$
```

Mis toodab järgmised kataloogid ja failid neisse:

```
~/repos/ylekahheldus$ ls -l test/
total 12
drwxr-xr-x 2 1022 1022 4096 dets  19 13:53 00
drwxr-xr-x 2 1022 1022 4096 dets  19 13:53 01
drwxr-xr-x 2 1022 1022 4096 dets  19 13:53 02
~/repos/ylekahheldus$ ls -l test/02
total 4464
-rw-r--r-- 1 1022 1022      94 dets  19 13:53 0_0.tfw
-rw-r--r-- 1 1022 1022 4564576 dets  19 13:53 0_0.tiff
~/repos/ylekahheldus$
```
