from genericpath import exists
from math import ceil
from os import makedirs
from os.path import join

import arcpy
from arcpy import env, Describe, Raster
from arcpy.da import InsertCursor, SearchCursor
from arcpy.sa import Con, BitwiseAnd

from macro_viewshed_analysis.config import TableNames as T, SaveLocations as S
from macro_viewshed_analysis.utils import OBSERVER_GROUP_SIZE, reproject, tmp_name, get_search_cursor


def create_temp_point_table(spatial_reference):
    fp = arcpy.CreateFeatureclass_management(
        T.IN_MEMORY, tmp_name(), 'POINT', has_z="ENABLED", spatial_reference=spatial_reference
    )

    arcpy.AddField_management(fp, T.Z, field_type='INTEGER')
    arcpy.AddField_management(fp, T.ISLAND_ID, field_type='LONG')
    arcpy.AddField_management(fp, T.SPLIT_ISLAND_ID, field_type='LONG')
    arcpy.AddField_management(fp, T.ISLAND_GRID_ID, field_type='LONG')
    arcpy.AddField_management(fp, T.VIEWPOINT_ID, field_type='LONG')
    arcpy.AddField_management(fp, T.OBSERVER, field_type='SHORT')
    return fp


def reset_tmp(spatial_reference, to_replace=None):
    if to_replace is not None:
        arcpy.Delete_management(to_replace)
    tmp_tbl = create_temp_point_table(spatial_reference)
    insert_cursor = InsertCursor(
        tmp_tbl,
        [
            T.SHAPE,
            T.Z,
            T.ISLAND_ID,
            T.SPLIT_ISLAND_ID,
            T.ISLAND_GRID_ID,
            T.VIEWPOINT_ID,
            T.OBSERVER
        ]
    )
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

    viewshed_folder = join(ws, S.FOLDER_VIEWSHEDS)
    tmp_table_folder = join(ws, S.FOLDER_TMP_OBSERVERS)
    point_table_folder = join(ws, S.FOLDER_OBSERVER_POINTS)
    for directory in [viewshed_folder, tmp_table_folder, point_table_folder]:
        if not exists(directory):
            makedirs(directory)

    arcpy.AddMessage("getting points")
    total_rows = int(arcpy.GetCount_management(viewpoints).getOutput(0))
    arcpy.AddMessage("{} viewpoints".format(total_rows))
    total_rasters = int(ceil(total_rows / float(OBSERVER_GROUP_SIZE)))
    arcpy.AddMessage("{} rasters".format(total_rasters))

    tmp_tbl, insert_cursor = reset_tmp(spatial_reference)
    with get_search_cursor(viewpoints, [T.SHAPE, T.Z, T.ISLAND_ID, T.SPLIT_ISLAND_ID, T.ISLAND_GRID_ID, T.ID]) as vp_sc:
        for i, row in enumerate(vp_sc):
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


def get_viewpoint_search_cursor(viewpoints, qry):
    """
    :rtype: (list[(int, (int, int, int, int))], SearchCursor)
    """
    return SearchCursor(viewpoints, ['FID_island', 'FID_split', 'FID_grid', 'OID@'], qry)


def save_table(fp, save_to):
    arcpy.AddMessage('Saving')
    try:
        if arcpy.Exists(save_to):
            arcpy.Append_management(fp, save_to)
            arcpy.AddMessage('New data appended to {}'.format(save_to))
        else:
            arcpy.CopyFeatures_management(fp, save_to)
            arcpy.AddMessage('New data saved to {}'.format(save_to))
    except Exception as e:
        arcpy.AddMessage('Failed to save data: {}'.format(e.message))


def get_poly_rasters(viewpoints, workspace, save_to, spatial_reference):
    failed = []
    if arcpy.Exists(save_to):
        fp = arcpy.CopyFeatures_management(save_to, join('in_memory', 'va_polygons'))
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
    sc = get_viewpoint_search_cursor(viewpoints, qry)
    try:
        for i, (island_id, split_island_id, grid_id, point_id) in enumerate(sc):
            if i % 100 == 0:
                save_table(fp, save_to)
            try:
                vs_num, index = divmod(point_id, OBSERVER_GROUP_SIZE)
                vs_num += 1  # Viewsheds are 1 indexed
                if vs_num != prev_vs:
                    prev_vs = vs_num
                    vs = 'viewshed_{:04d}'.format(vs_num)
                    if not arcpy.Exists(vs):
                        vs_disk = join(workspace, 'viewsheds', 'viewshed_{:04d}'.format(vs_num))
                        arcpy.CopyRaster_management(vs_disk, vs)
                    print(vs)
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

                arcpy.Delete_management(extracted)
                arcpy.Delete_management(vs_poly)
            except Exception as e:
                arcpy.AddError('Failed! vs_num={}, point_id=point_id={}. {}'.format(vs_num, point_id, e.message))
                failed.append((i, island_id, split_island_id, grid_id, point_id, e.__class__.__name__, e.message))
    finally:
        # Clean up the cursors
        del ic
        del sc
        arcpy.AddMessage('Saving')
        try:
            if arcpy.Exists(save_to):
                arcpy.Append_management(fp, save_to)
                arcpy.AddMessage('New data appended to {}'.format(save_to))
            else:
                arcpy.CopyFeatures_management(fp, save_to)
                arcpy.AddMessage('New data saved to {}'.format(save_to))
        except Exception as e:
            arcpy.AddMessage('Failed to save data: {}'.format(e.message))
        arcpy.AddMessage('Failed: {}'.format(failed))
        arcpy.AddMessage('Done!')
