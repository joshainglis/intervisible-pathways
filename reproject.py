from os import mkdir
from os.path import join, exists

import arcpy
from arcpy import env
from arcpy.da import InsertCursor, SearchCursor
from arcpy.sa import Con, Raster
from math import ceil

workspace = arcpy.GetParameterAsText(0)
dem = arcpy.GetParameterAsText(1)
low_sea_level = int(arcpy.GetParameterAsText(2))
high_sea_level = int(arcpy.GetParameterAsText(3))
sea_level_steps = int(arcpy.GetParameterAsText(4))
out_workspace = arcpy.GetParameterAsText(5)
overwrite_existing = bool(eval(arcpy.GetParameterAsText(6).title()))

# workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch')
env.workspace = workspace
env.overwriteOutput = True

SEA_LEVELS = xrange(low_sea_level, high_sea_level, sea_level_steps)
OBSERVER_GROUP_SIZE = 32

arcpy.CheckOutExtension("Spatial")
arcpy.CheckOutExtension("3D")


def create_temp_point_table(spatial_reference):
    fp = arcpy.CreateFeatureclass_management(
        'in_memory', 'temp_points', 'POINT', has_z="ENABLED", spatial_reference=spatial_reference
    )

    arcpy.AddField_management(fp, 'Z', field_type='INTEGER')
    arcpy.AddField_management(fp, 'FID_island', field_type='LONG')
    arcpy.AddField_management(fp, 'FID_split_', field_type='LONG')
    arcpy.AddField_management(fp, 'FID_grid', field_type='LONG')
    arcpy.AddField_management(fp, 'FID_point', field_type='LONG')
    arcpy.AddField_management(fp, 'observer', field_type='SHORT')
    return fp


def reset_tmp(to_replace=None):
    if to_replace is not None:
        arcpy.Delete_management(to_replace)
    tmp_tbl = create_temp_point_table(spatial_reference)
    search_cursor = InsertCursor(tmp_tbl, ['SHAPE@', 'Z', 'FID_island', 'FID_split_', 'FID_grid', 'FID_point', 'observer'])
    return tmp_tbl, search_cursor


gebco_vert = join(workspace, 'gebco_vert')
if not exists(gebco_vert):
    arcpy.AddMessage("Reprojecting")
    reprojected = arcpy.ProjectRaster_management(
        in_raster=dem,
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

for sea_level in SEA_LEVELS:
    ws = join(out_workspace, 'sl_{}'.format(sea_level))
    viewpoints = join(ws, "gridded_viewpoints.shp")

    arcpy.AddMessage("Making sea level raster")
    gv = Raster(gebco_vert)
    sea_level_raster = Con(gv <= sea_level, sea_level, gv)

    spatial_reference = arcpy.Describe(sea_level_raster).spatialReference

    viewshed_folder = join(ws, 'viewsheds')
    tmp_table_folder = join(ws, 'observer_groups')
    point_table_folder = join(ws, 'observer_points')
    for directory in [viewshed_folder, tmp_table_folder, point_table_folder]:
        if not exists(directory):
            mkdir(directory)

    arcpy.AddMessage("getting points")
    total_rows = int(arcpy.GetCount_management(viewpoints).getOutput(0))
    arcpy.AddMessage("{} viewpoints".format(total_rows))
    total_rasters = int(ceil(total_rows / float(OBSERVER_GROUP_SIZE)))
    arcpy.AddMessage("{} rasters".format(total_rasters))

    # noinspection PyRedeclaration
    tmp_table, sc = reset_tmp()
    for i, row in enumerate(SearchCursor(viewpoints, ['SHAPE@', 'Z', 'FID_island', 'FID_split_', 'FID_grid', 'FID'])):
        d, m = divmod(i, OBSERVER_GROUP_SIZE)
        if (i > 0 and m == 0) or (i == (total_rows - 1)):
            c = d + int(m > 0)

            save_raster_to = join(viewshed_folder, 'viewshed_{:04d}'.format(c))
            save_observers_to = join(ws, "tst_points_{:04d}".format(c))
            save_observer_relations_to = join(tmp_table_folder, 'observer_relations_{:04d}'.format(c))
            save_dirs = [save_raster_to, save_observers_to, save_observer_relations_to]

            if (not overwrite_existing) and all(exists(path) for path in save_dirs):
                tmp_table, sc = reset_tmp(tmp_table)
                continue

            arcpy.CopyFeatures_management(tmp_table, save_observers_to)

            arcpy.AddMessage("doing viewshed {} of {}".format(c, total_rasters))
            out_raster, _, _ = arcpy.Viewshed2_3d(
                in_raster=sea_level_raster,
                in_observer_features=tmp_table,
                out_raster=save_raster_to,
                out_agl_raster=None,
                analysis_type="OBSERVERS",
                vertical_error="0 Meters",
                out_observer_region_relationship_table=save_observer_relations_to,
                refractivity_coefficient="0.13",
                surface_offset="0 Meters",
                observer_elevation="Z",
                observer_offset="2 Meters",
                inner_radius=None,
                inner_radius_is_3d="GROUND",
                outer_radius="300 Kilometers",
                outer_radius_is_3d="GROUND",
                horizontal_start_angle="0",
                horizontal_end_angle="360",
                vertical_upper_angle="90",
                vertical_lower_angle="-90",
                analysis_method="PERIMETER_SIGHTLINES"
            )

            tmp_table, sc = reset_tmp(tmp_table)
        sc.insertRow(row + (i % OBSERVER_GROUP_SIZE,))

    arcpy.AddMessage("done getting points")
