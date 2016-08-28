from arcgisscripting import Raster
from contextlib import contextmanager
from genericpath import exists
from os import mkdir, makedirs
from os.path import join, split, dirname
from uuid import uuid4

import arcpy
from arcpy import AddMessage, Exists, CopyFeatures_management
from arcpy.sa import ExtractByMask

from macro_viewshed_analysis.config import TableNames as T

OBSERVER_GROUP_SIZE = 32


@contextmanager
def cleanup(object_type, *args, **kwargs):
    obj = object_type(*args, **kwargs)
    yield obj
    del obj


@contextmanager
def get_search_cursor(in_table, field_names, where_clause=None, spatial_reference=None, explode_to_points=None,
                      sql_clause=(None, None)):
    """
    :type in_table: str | arcpy.FeatureSet
    :type field_names: list[str]
    :type where_clause: str
    :type spatial_reference: arcpy.SpatialReference
    :type explode_to_points: bool
    :type sql_clause: (str, str)
    :rtype: collections.Iterable
    """
    with cleanup(arcpy.da.SearchCursor, in_table, field_names, where_clause, spatial_reference, explode_to_points,
                 sql_clause) as cursor:
        yield cursor


@contextmanager
def get_insert_cursor(in_table, field_names):
    """
    :type in_table: str | arcpy.FeatureSet
    :type field_names: list[str]
    :rtype: arcpy.da.InsertCursor
    """
    with cleanup(arcpy.da.InsertCursor, in_table, field_names) as cursor:
        yield cursor


def create_dirs(dirs):
    """
    :type dirs: str | list[str]
    """
    if isinstance(dirs, basestring):
        dirs = [dirs]
    for directory in dirs:
        if not exists(directory):
            arcpy.AddMessage("Creating directory: {}".format(directory))
            mkdir(directory)


def tmp_name():
    return 'tmp{}'.format(uuid4().hex)


def in_mem(var):
    """
    :param var: str
    :return: str
    """
    return join(T.IN_MEMORY, var)


def get_output_loc(given, default):
    return in_mem(default) if given is None else given


def get_field_names(shp):
    """
    :type shp: str | arcpy.FeatureSet
    :rtype: list[str]
    """
    return [f.name for f in arcpy.ListFields(shp)]


def print_fields(shp):
    AddMessage('{}: {}'.format(shp, map(str, get_field_names(shp))))


def get_spatial_reference(obj):
    return arcpy.Describe(obj).spatialReference


def reproject(sea_level_raster):
    slr_dir, slr_file = split(sea_level_raster)
    gebco_vert = join(slr_dir, "vert_{}".format((slr_file.rsplit('.')[0])[:8]))
    if not (slr_file.startswith("vert_") or exists(gebco_vert)):
        arcpy.AddMessage("Reprojecting")
        gebco_vert = arcpy.ProjectRaster_management(
            in_raster=sea_level_raster,
            out_raster=gebco_vert,
            out_coor_system=("GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],"
                             "PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],"
                             "VERTCS['WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],"
                             "PARAMETER['Vertical_Shift',0.0],PARAMETER['Direction',1.0],UNIT['Meter',1.0]]"),
            resampling_type="BILINEAR",
            in_coor_system=("GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],"
                            "PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]")
        )
        arcpy.AddMessage("Finished reprojecting")
    return gebco_vert


def extract_region_of_interest(dem, region_of_interest):
    arcpy.AddMessage("Extracting ")
    with get_search_cursor(region_of_interest, [T.SHAPE]) as sc:
        (roi,) = sc.next()
    rect_extract = ExtractByMask(dem, roi)
    raster = Raster(rect_extract)
    return raster


def run_func(overwrite_existing, out_workspace, save_loc, save_intermediate, creation_message, func, args, kwargs):
    save_to = join(out_workspace, save_loc)
    save_dir = dirname(save_to)
    if not exists(save_dir):
        makedirs(save_dir)
    if (Exists(save_to) or exists(save_to)) and not overwrite_existing:
        arcpy.AddMessage("Using existing file at {}".format(save_to))
        return save_to
    arcpy.AddMessage(creation_message)
    out_var = func(*args, **kwargs)
    if save_intermediate:
        arcpy.AddMessage("Saving {} to {}".format(save_loc, save_to))
        CopyFeatures_management(out_var, save_to)
    return out_var
