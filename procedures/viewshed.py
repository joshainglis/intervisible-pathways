from arcgisscripting import Raster
from genericpath import exists
from math import ceil
from os import makedirs
from os.path import join

import arcpy
from arcpy import env, Describe
from arcpy.da import InsertCursor, SearchCursor
from arcpy.sa import Con, BitwiseAnd

from utils import OBSERVER_GROUP_SIZE, reproject, in_mem


def create_temp_point_table(spatial_reference):
    fp = arcpy.CreateFeatureclass_management(
        'in_memory', 'temp_points', 'POINT', has_z="ENABLED", spatial_reference=spatial_reference
    )

    arcpy.AddField_management(fp, 'Z', field_type='INTEGER')
    arcpy.AddField_management(fp, 'FID_island', field_type='LONG')
    arcpy.AddField_management(fp, 'FID_split', field_type='LONG')
    arcpy.AddField_management(fp, 'FID_grid', field_type='LONG')
    arcpy.AddField_management(fp, 'FID_point', field_type='LONG')
    arcpy.AddField_management(fp, 'observer', field_type='SHORT')
    return fp


def reset_tmp(spatial_reference, to_replace=None):
    if to_replace is not None:
        arcpy.Delete_management(to_replace)
    tmp_tbl = create_temp_point_table(spatial_reference)
    insert_cursor = InsertCursor(tmp_tbl,
                                 ['SHAPE@', 'Z', 'FID_island', 'FID_split', 'FID_grid', 'FID_point', 'observer'])
    return tmp_tbl, insert_cursor


def run_multi_viewshed(tmp_table, d, m,
                       viewshed_folder, point_table_folder, tmp_table_folder, sea_level_raster, spatial_reference,
                       total_rasters,
                       overwrite_existing=False):
    c = d + int(m > 0)

    save_raster_to = join(viewshed_folder, 'viewshed_{:04d}'.format(c))
    save_observers_to = join(point_table_folder, "tst_points_{:04d}.shp".format(c))
    save_observer_relations_to = join(tmp_table_folder, 'observer_relations_{:04d}.shp'.format(c))
    save_dirs = [save_raster_to, save_observers_to, save_observer_relations_to]

    if (not overwrite_existing) and all(exists(path) for path in save_dirs):
        return reset_tmp(spatial_reference, tmp_table)

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

    return reset_tmp(spatial_reference, tmp_table)


def get_viewshed_groups(tmp_tbl, insert_cursor, row, i, total_rows,
                        viewshed_folder, ws, tmp_table_folder, sea_level_raster, spatial_reference, total_rasters,
                        overwrite_existing):
    d, m = divmod(i, OBSERVER_GROUP_SIZE)
    if (i > 0 and m == 0) or (i == (total_rows - 1)):
        tmp_tbl, insert_cursor = run_multi_viewshed(
            tmp_tbl, d, m,
            viewshed_folder, ws, tmp_table_folder, sea_level_raster, spatial_reference, total_rasters,
            overwrite_existing
        )
    insert_cursor.insertRow(row + (i % OBSERVER_GROUP_SIZE,))
    return tmp_tbl, insert_cursor


def run_all_viewsheds(sea_level, ws, viewpoints, dem, spatial_reference=None, overwrite_existing=False):
    env.overwriteOutput = True
    if spatial_reference is None:
        spatial_reference = Describe(dem).spatialReference

    dem = reproject(dem)
    r = Raster(dem)
    slr = Con(r > sea_level, r, sea_level)

    viewshed_folder = join(ws, 'viewsheds')
    tmp_table_folder = join(ws, 'observer_groups')
    point_table_folder = join(ws, 'observer_points')
    for directory in [viewshed_folder, tmp_table_folder, point_table_folder]:
        if not exists(directory):
            makedirs(directory)

    arcpy.AddMessage("getting points")
    total_rows = int(arcpy.GetCount_management(viewpoints).getOutput(0))
    arcpy.AddMessage("{} viewpoints".format(total_rows))
    total_rasters = int(ceil(total_rows / float(OBSERVER_GROUP_SIZE)))
    arcpy.AddMessage("{} rasters".format(total_rasters))

    tmp_tbl, insert_cursor = reset_tmp(spatial_reference)
    for i, row in enumerate(SearchCursor(viewpoints, ['SHAPE@', 'Z', 'FID_island', 'FID_split', 'FID_grid', 'FID'])):
        tmp_tbl, insert_cursor = get_viewshed_groups(
            tmp_tbl, insert_cursor, row, i, total_rows,
            viewshed_folder, point_table_folder, tmp_table_folder, slr, spatial_reference, total_rasters,
            overwrite_existing)
    env.overwriteOutput = overwrite_existing


def extract_viewshed(workspace, viewshed_folder, vs_num):
    viewpoints = join(workspace, "tst_points_{:04d}.shp".format(vs_num))

    r = Raster(join(workspace, 'viewsheds', 'viewshed_{:04d}'.format(vs_num)))

    vs_dir = join(viewshed_folder, '{:03d}'.format(vs_num))
    if not exists(vs_dir):
        makedirs(vs_dir)

    for i, row in enumerate(SearchCursor(viewpoints, ['FID', 'FID_split_'])):
        try:
            print("{:03d}: {}".format(vs_num, row))
            val = 1 if row[0] < 31 else -1
            extracted = Con(BitwiseAnd(r, (val << int(row[0]))), 1, None)
            extracted.save(join(vs_dir, 'v{:03d}i{:05d}o{:02d}'.format(vs_num, row[1], row[0])))
        except Exception as e:
            print("Problem on {}-{}: {}".format(vs_num, i, e.message))


def get_poly_rasters(viewpoints, workspace, spatial_reference):
    if arcpy.Exists('viewshed_polys.shp'):
        fp = arcpy.CopyFeatures_management('viewshed_polys.shp', join('in_memory', 'va_polygons'))
    else:
        fp = arcpy.CreateFeatureclass_management(
            'in_memory', 'va_polygons', 'POLYGON', spatial_reference=spatial_reference
        )

        arcpy.AddField_management(fp, 'FID_island', field_type='LONG')
        arcpy.AddField_management(fp, 'FID_split', field_type='LONG')
        arcpy.AddField_management(fp, 'FID_grid', field_type='LONG')
        arcpy.AddField_management(fp, 'FID_point', field_type='LONG')
    # arcpy.AddIndex_management(fp, 'FID_island', 'island_idx')
    ic = arcpy.da.InsertCursor(fp, ['SHAPE@', 'FID_island', 'FID_split', 'FID_grid', 'FID_point'])

    if int(arcpy.GetCount_management(fp).getOutput(0)) > 0:
        highest_point = max(p for (p,) in arcpy.da.SearchCursor(fp, ['FID_point']))
        qry = """{} > {}""".format(arcpy.AddFieldDelimiters(viewpoints, 'FID'), highest_point)
    else:
        qry = None

    arcpy.AddMessage('Starting')
    prev_vs = 0
    r = None
    try:
        for i, (island_id, split_island_id, grid_id, point_id) in enumerate(
            SearchCursor(viewpoints, ['FID_island', 'FID_split', 'FID_grid', 'FID'], qry)):
            vs_num, index = divmod(point_id, OBSERVER_GROUP_SIZE)
            vs_num += 1
            if vs_num != prev_vs:
                vs = join(workspace, 'viewsheds', 'viewshed_{:04d}'.format(vs_num))
                r = Raster(vs)

            arcpy.AddMessage(
                'Running: vs_num={}, index={}, island_id={}, split_island_id={}, grid_id={}, point_id={}'.format(
                    vs_num, index, island_id, split_island_id, grid_id, point_id
                )
            )
            val = 1 if index < 31 else -1
            extracted = Con(BitwiseAnd(r, (val << int(index))), 1, None)
            vs_poly = arcpy.RasterToPolygon_conversion(
                in_raster=extracted,
                out_polygon_features=join('in_memory', 'vs_poly_{}_{}'.format(island_id, i)),
            )
            for (poly,) in SearchCursor(vs_poly, ["SHAPE@"]):
                ic.insertRow((poly, island_id, split_island_id, grid_id, point_id))
    finally:
        # Clean up the insert cursor
        del ic
        arcpy.AddMessage('Saving')
        try:
            if arcpy.Exists('viewshed_polys.shp'):
                arcpy.Append_management(fp, 'viewshed_polys.shp')
                arcpy.AddMessage('New data appended to viewshed_polys.shp')
            else:
                arcpy.CopyFeatures_management(fp, 'viewshed_polys.shp')
                arcpy.AddMessage('New data saved to viewshed_polys.shp')
        except Exception as e:
            arcpy.AddMessage('Failed to save data: {}'.format(e.message))
        arcpy.AddMessage('Done!')