import argparse
import logging
import sys
from os.path import join, exists
from os import mkdir

import fiona
import rasterio
from numpy import bitwise_and, bool_, uint8
from rasterio.features import shapes

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('rasterio_polygonize')


def polygonize(raster_file, vector_file):
    with rasterio.drivers():
        with rasterio.open(raster_file) as src:
            image = src.read(1)
            nodata = int(src.nodatavals[0])
            m = image != nodata
            logger.info(m.sum())
            logger.info("%s %s %s %d-%d", image.dtype, bin(nodata), image.shape, image.min(), image.max())

    for i in xrange(32):
        val = 1 if i < 31 else -1
        mask = bitwise_and(image, (val << i)).astype(bool_) & m
        img = mask.astype(uint8)
        logger.info("t: %d val: %d, mask: %d, img: %d", i, val, mask.sum(), img.sum())

        results = (
            {'properties': {'raster_val': v}, 'geometry': s} for i, (s, v)
            in enumerate(shapes(img, mask=mask, connectivity=8, transform=src.affine)))

        with fiona.open(
            "{}_{:04d}.shp".format(vector_file, i), 'w',
            driver="ESRI Shapefile",
            crs=src.crs.data,
            schema={'properties': [('raster_val', 'int')], 'geometry': 'Polygon'}) \
            as dst:
            dst.writerecords(results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Writes shapes of raster features to a vector file")
    parser.add_argument(
        'input',
        metavar='INPUT',
        help="Input file name")
    parser.add_argument(
        'output',
        metavar='OUTPUT',
        help="Output file name")
    parser.add_argument(
        '--output-driver',
        metavar='OUTPUT DRIVER',
        help="Output vector driver name")
    parser.add_argument(
        '--mask-value',
        default=None,
        type=int,
        metavar='MASK VALUE',
        help="Value to mask")
    args = parser.parse_args()

    for i in xrange(1, 134):
        f = 'viewshed_{:04d}'.format(i)
        infile = join(args.input, f)
        outfolder = join(args.output, f)
        if not exists(outfolder):
            mkdir(outfolder)
        outfile = join(outfolder, f)
        polygonize(infile, outfile)

        # print subprocess.check_output(
        #     ['ogrinfo', '-so', args.output, name])
