"""

"""

import logging
import re
import sys
from os import mkdir, getenv, listdir
from os.path import join, exists

import click
import fiona
import rasterio
from numpy import bitwise_and, bool_, uint8
from rasterio.features import shapes

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('__name__')

VIEWSHEDS_PER_FILE = int(getenv('VIEWSHEDS_PER_FILE', 32))
OVERFLOW = int(getenv('OVERFLOW', 31))


def save_to_shapefile(poly_generator, raster, vector_file, vs_index):
    """
    :type poly_generator: collections.Iterable[(dict, int)]
    :type vs_index: int
    :type raster: rasterio.io.DatasetReader
    :type vector_file: str
    """
    with fiona.open(
        "{}_{:04d}.shp".format(vector_file, vs_index), 'w',
        driver="ESRI Shapefile",
        crs=raster.crs.data,
        schema={
            'properties': [('raster_val', 'int')],
            'geometry': 'Polygon'
        }
    ) as dst:
        dst.writerecords(poly_generator)


def raster_to_poly(viewshed_raster, viewshed_mask, raster, connectivity=8):
    """
    :type viewshed_raster: numpy.ndarray
    :type viewshed_mask: numpy.ndarray
    :type raster: rasterio.io.DatasetReader
    :type connectivity: int
    :rtype: collections.Iterable[(dict, int)]
    """
    return (
        {'properties': {'raster_val': v}, 'geometry': s} for s, v
        in shapes(viewshed_raster, mask=viewshed_mask, connectivity=connectivity, transform=raster.affine)
    )


def separate_viewshed(vs_index, overflow, viewshed_layer, valid_data_mask):
    """
    :type vs_index: int
    :type overflow: int
    :type viewshed_layer: numpy.ndarray
    :type valid_data_mask: numpy.ndarray
    :rtype: (numpy.ndarray, numpy.ndarray)
    """
    val = 1 if vs_index < overflow else -1
    mask = bitwise_and(viewshed_layer, (val << vs_index)).astype(bool_) & valid_data_mask
    img = mask.astype(uint8)
    logger.info("index: %d, mask: %d, img: %d", vs_index, mask.sum(), img.sum())

    return img, mask


def separate_viewsheds(viewsheds_per_file, overflow, viewshed_layer, valid_data_mask, vector_file, raster):
    """
    :type viewsheds_per_file: int
    :type overflow: int
    :type viewshed_layer: numpy.ndarray
    :type valid_data_mask: numpy.ndarray
    :type vector_file: str
    :type raster: rasterio.io.DatasetReader
    """
    for vs_index in xrange(viewsheds_per_file):
        img, mask = separate_viewshed(vs_index, overflow, viewshed_layer, valid_data_mask)
        poly_generator = raster_to_poly(img, mask, raster)
        save_to_shapefile(poly_generator, raster, vector_file, vs_index)


def separate_viewsheds_and_convert_to_polygons(raster_file, vector_file,
                                               viewsheds_per_file=VIEWSHEDS_PER_FILE, overflow=OVERFLOW):
    """
    :type raster_file: str
    :type vector_file: str
    :type viewsheds_per_file: int
    :type overflow: int
    """
    with rasterio.drivers():
        with rasterio.open(raster_file) as raster:
            viewshed_layer = raster.read(1)
            nodata_value = int(raster.nodatavals[0])
            valid_data_mask = viewshed_layer != nodata_value
            logger.info("%s", raster_file)
            separate_viewsheds(viewsheds_per_file, overflow, viewshed_layer, valid_data_mask, vector_file, raster)


@click.command()
@click.option('--input-folder', '-i',
              type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True, writable=True),
              default='/in')
@click.option('--output-folder', '-o',
              type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True, writable=True),
              default='/out')
@click.option('--viewshed-file-regex', '-v', default='^viewshed_\d+$', type=click.STRING)
@click.option('--viewsheds-per-file', '-n', default=32, type=click.INT)
@click.option('--overflow', '-f', default=31, type=click.INT)
def run(input_folder, output_folder, viewshed_file_regex, viewsheds_per_file, overflow):
    """
    :type input_folder: str
    :type output_folder: str
    :type viewshed_file_regex: str
    :type viewsheds_per_file: int
    :type overflow: int
    """
    vs_re = re.compile(viewshed_file_regex)
    for viewshed_file in (y for y in listdir(input_folder) if vs_re.match(y)):
        infile = join(input_folder, viewshed_file)
        out_folder = join(output_folder, viewshed_file)
        if not exists(out_folder):
            mkdir(out_folder)
        outfile = join(out_folder, viewshed_file)
        separate_viewsheds_and_convert_to_polygons(infile, outfile, viewsheds_per_file, overflow)


if __name__ == '__main__':
    run()
