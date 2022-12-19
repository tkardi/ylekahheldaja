import argparse
import csv
import logging
import os
import subprocess

LOG_FORMAT="%(asctime)s; %(levelname)s; %(message)s"
logging.basicConfig(format=LOG_FORMAT)
logger = logging.getLogger(__file__)

_path = os.path.dirname(__file__)

class SubprocessMixin(object):
    def _run(self, command, **kwargs):
        """Run a subprocess command"""
        params=dict(
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            encoding="utf8"
        )
        k = {}
        if "input" in kwargs:
            k["input"] = kwargs.pop("input")
        kwargs.update(params)
        output, err = subprocess.Popen(command, **kwargs).communicate(**k)
        [logger.debug(_output) for _output in output.split("\n")]
        if err:
            [logger.warning(_err) for _err in err.split("\n")]
            raise AttributeError(err)
        return output

class Retiler(SubprocessMixin):
    def _run(self, cmd, **kwargs):
        logger.debug(" ".join(cmd))
        return super(Retiler, self)._run(cmd, **kwargs)

    def makeoutputpath(self, path):
        if os.path.exists(path) == False:
            logger.info(f"Path {path} does not exist. Creating...")
            os.makedirs(path)
        logger.debug(f"Saving tiles to {path}")
        return path

    def loop_zooms(self, minzoom, maxzoom):
        for i in range(minzoom, maxzoom+1, 1):
            z = f"0{i}"[-2:]
            zoompath = os.path.join(_path, "..", "resources", "zooms", f"{z}.csv")
            try:
                assert os.path.exists(zoompath)
            except AssertionError as ae:
                logger.exception(ae)
                raise
            logger.info(f"ZOOM {z} from {zoompath}")
            yield dict(
                path=zoompath,
                zoom=z
            )

    def build_tiles(self, outpath, layer, **kwargs):
        # compose filename
        fn = os.path.join(outpath, f"{kwargs['x']}_{kwargs['y']}.tiff")

        # save tile
        cmd = [
            "gdal_translate",
            "-co", "COMPRESS=LZW", "-co", "TILED=YES", "-co", "TFW=YES",
            "-projwin_srs", "EPSG:3301",
            "-projwin", kwargs["minx"], kwargs["maxy"], kwargs["maxx"], kwargs["miny"],
            "-outsize", kwargs["width"], kwargs["width"],
            layer,
            fn
        ]
        self._run(cmd)

        # build pyramids
        cmd = [
            "gdaladdo", fn, "3"
        ]
        self._run(cmd)

    def loop_requests(self, zoompath, outpath, layer):
        with open(zoompath["path"], encoding="utf-8-sig") as f:
            z = zoompath["zoom"]
            outpath = self.makeoutputpath(os.path.join(outpath, z))
            [
                self.build_tiles(
                    outpath, layer, **row
                ) for row in csv.DictReader(f, delimiter=",")
            ]

    def run(self, layername, **kwargs):
        layer = os.path.join(_path, "..", "resources", "server", f"{layername}.xml")
        try:
            assert os.path.exists(layer)
        except AssertionError as ae:
            logger.exception(ae)
            raise

        minzoom = kwargs["minzoom"]
        maxzoom = kwargs["maxzoom"]
        outpath = kwargs["outpath"]

        [
            self.loop_requests(
                zoompath,
                outpath,
                layer
            ) for zoompath in self.loop_zooms(minzoom, maxzoom)
        ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog=__file__)
    parser.add_argument(
        "-m", "--minzoom",
        help="minzoom value. Defaults to 0", type=int,
        default=0
    )
    parser.add_argument(
        "-x", "--maxzoom",
        help="maxzoom value. Defaults to 11", type=int,
        default=11
    )
    parser.add_argument(
        "-l", "--loglevel",
        help="Log level. Defaults to INFO", type=str,
        default="INFO"
    )

    args = parser.parse_args()
    kwargs = args.__dict__
    kwargs["outpath"] = "/data"

    logger.setLevel(kwargs.pop("loglevel"))

    r = Retiler()
    r.run(
        "ma-kaart",
        **kwargs
    )
