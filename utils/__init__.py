from arcgisscripting import Raster
from genericpath import exists
from os import mkdir, makedirs
from os.path import join, split, dirname

import arcpy
from arcpy import AddMessage, Exists, CopyFeatures_management
from arcpy.da import SearchCursor
from arcpy.sa import ExtractByMask

OBSERVER_GROUP_SIZE = 32


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


def in_mem(var):
    """
    :param var: str
    :return: str
    """
    return join('in_memory', var)


def get_output_loc(given, default):
    return in_mem(default) if given is None else given


def get_field_names(shp):
    """
    :type shp: str
    :rtype: list[str]
    """
    return [f.name for f in arcpy.ListFields(shp)]


def print_fields(shp):
    AddMessage('{}: {}'.format(shp, map(str, get_field_names(shp))))


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
    (roi,) = SearchCursor(region_of_interest, ['SHAPE@']).next()
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
