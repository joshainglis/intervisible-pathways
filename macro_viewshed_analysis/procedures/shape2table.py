from os.path import join

import arcpy

from macro_viewshed_analysis.config import TableNames as T, SaveLocations as S
from macro_viewshed_analysis.utils import OBSERVER_GROUP_SIZE, get_search_cursor as gsc, get_insert_cursor as gic, \
    tmp_name


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


def get_or_create_table(save_to, spatial_reference):
    if arcpy.Exists(save_to):
        fp = arcpy.CopyFeatures_management(save_to, join(T.IN_MEMORY, tmp_name()))
    else:
        fp = arcpy.CreateFeatureclass_management(
            T.IN_MEMORY, tmp_name(), 'POLYGON', spatial_reference=spatial_reference
        )

        arcpy.AddField_management(fp, T.ISLAND_ID, field_type='LONG')
        arcpy.AddField_management(fp, T.SPLIT_ISLAND_ID, field_type='LONG')
        arcpy.AddField_management(fp, T.ISLAND_GRID_ID, field_type='LONG')
        arcpy.AddField_management(fp, T.VIEWPOINT_ID, field_type='LONG')
    return fp


def generate_last_completed_query(fp, viewpoints):
    if int(arcpy.GetCount_management(fp).getOutput(0)) > 0:
        highest_point = max(p for (p,) in arcpy.da.SearchCursor(fp, [T.VIEWPOINT_ID]))
        qry = """{} > {}""".format(arcpy.AddFieldDelimiters(viewpoints, T.FID), highest_point)
    else:
        qry = None
    return qry


def log_and_save(fp, save_to, i, log_every, save_every):
    if log_every and i % log_every == 0:
        arcpy.AddMessage("Viewpoint: {}".format(i))
        if save_every and i % save_every == 0:
            save_table(fp, save_to)


def clean_up(fp, save_to, failed):
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


def poly_to_table(viewpoints, save_to, spatial_reference, log_every=100, save_every=5000,
                  observer_group_size=OBSERVER_GROUP_SIZE):
    failed = []
    fp = get_or_create_table(save_to, spatial_reference)
    qry = generate_last_completed_query(fp, viewpoints)

    arcpy.AddMessage('Starting')
    insert_table_cols = [T.SHAPE, T.ISLAND_ID, T.SPLIT_ISLAND_ID, T.ISLAND_GRID_ID, T.VIEWPOINT_ID]
    search_table_cols = [T.ISLAND_ID, T.SPLIT_ISLAND_ID, T.ISLAND_GRID_ID, T.ID]
    with gic(fp, insert_table_cols) as ic, gsc(viewpoints, search_table_cols, qry) as sc:
        try:
            for i, (island_id, split_island_id, grid_id, point_id) in enumerate(sc):
                log_and_save(fp, save_to, i, log_every, save_every)
                vs_num, index = divmod(point_id, observer_group_size)
                vs_num += 1  # Viewsheds are 1 indexed
                vs = S.individual_viewshed_polygon_save_location(vs_num, index)
                try:
                    with gsc(vs, [T.SHAPE]) as vs_sc:
                        for (poly,) in vs_sc:
                            ic.insertRow((poly, island_id, split_island_id, grid_id, point_id))
                except Exception as e:
                    arcpy.AddError('Failed! vs_num={}, point_id=point_id={}. {}'.format(vs_num, point_id, e.message))
                    failed.append((i, island_id, split_island_id, grid_id, point_id, e.__class__.__name__, e.message))
        finally:
            clean_up(fp, save_to, failed)
