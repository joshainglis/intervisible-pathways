from os.path import join

import arcpy
from arcpy.da import SearchCursor

from utils import OBSERVER_GROUP_SIZE


def get_search_cursor(viewpoints, qry):
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


def poly_to_table(viewpoints, save_to, spatial_reference):
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
    sc = get_search_cursor(viewpoints, qry)
    try:
        for i, (island_id, split_island_id, grid_id, point_id) in enumerate(sc):
            if i % 100 == 0:
                save_table(fp, save_to)
            try:
                vs_num, index = divmod(point_id, OBSERVER_GROUP_SIZE)
                vs_num += 1  # Viewsheds are 1 indexed
                # if vs_num != prev_vs:
                #     prev_vs = vs_num
                vs = r'viewshed_{0:04d}\viewshed_{0:04d}_{1:04d}.shp'.format(vs_num, index)

                for (poly,) in SearchCursor(vs, ["SHAPE@"]):
                    ic.insertRow((poly, island_id, split_island_id, grid_id, point_id))

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
