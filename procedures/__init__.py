from arcgisscripting import Raster
from genericpath import exists
from math import ceil
from os import makedirs
from os.path import join

import arcpy
from arcpy import Exists, env, Describe, Buffer_analysis, Intersect_analysis, GridIndexFeatures_cartography, \
    RasterToPolygon_conversion, RasterToMultipoint_3d, CreateFeatureclass_management, AddField_management
from arcpy.da import InsertCursor, SearchCursor
from arcpy.sa import Con

from utils import get_output_loc, print_fields, in_mem, OBSERVER_GROUP_SIZE, reproject


def create_sea_level_island_polygons(base_raster, sea_level, output_to=None, overwrite_existing=False):
    """

    :param base_raster:
    :param sea_level:
    :param output_to:
    :return: ['OBJECTID', 'Shape', 'Id', 'gridcode']
    """
    output_to = get_output_loc(output_to, 'islands')
    if Exists(output_to) and not overwrite_existing:
        return output_to, True

    r = Raster(base_raster)
    islands = Con(r > sea_level, 1, None)  # type: Raster
    islands_poly = RasterToPolygon_conversion(
        in_raster=islands,
        out_polygon_features=output_to,
    )
    print_fields(islands_poly)
    # ['OBJECTID', 'Shape', 'Id', 'gridcode']
    return islands_poly, False


def create_island_inner_buffers(region_of_interest, islands_poly, distance_to_shore, output_to=None):
    """
    :param region_of_interest: A polygon that constrains the area to be looked at
    :type region_of_interest: str
    :param islands_poly: The islands feature. This should be a polygon feature class representing land masses
    :type islands_poly: str
    :param distance_to_shore: Linear Unit representing the inner buffer to be created from the shoreline
    :type distance_to_shore: str
    :return: An inner buffer of the islands features intersected with the region of interest.
             ['FID', 'Shape', 'FID_island', 'Id', 'gridcode', 'BUFF_DIST', 'ORIG_FID', 'FID_roi', 'Id_1']
    :rtype: str
    """
    output_to = get_output_loc(output_to, 'borders')

    borders = Buffer_analysis(
        in_features=islands_poly,
        out_feature_class=in_mem('borders_tmp'),
        buffer_distance_or_field="-{}".format(distance_to_shore),
        line_side='OUTSIDE_ONLY',
        dissolve_option='NONE',
        method='GEODESIC'
    )
    print_fields(borders)
    # ['OBJECTID', 'Shape', 'Id', 'gridcode', 'BUFF_DIST', 'ORIG_FID']

    borders = Intersect_analysis([borders, region_of_interest], output_to)
    print_fields(borders)
    # ['OBJECTID', 'Shape', 'FID_borders_tmp', 'Id', 'gridcode', 'BUFF_DIST', 'ORIG_FID', 'FID_roi', 'Id_1']

    return borders


def create_grid(in_features, grid_width, grid_height, output_to=None):
    """
    Create a grid over the island buffers

    :param in_features:
    :param grid_width:
    :param grid_height:
    :param output_to:
    :return:
    """
    output_to = get_output_loc(output_to, 'grid')

    grid = GridIndexFeatures_cartography(
        out_feature_class=output_to,
        in_features=in_features,
        intersect_feature='INTERSECTFEATURE',
        polygon_width=grid_width,
        polygon_height=grid_height,
    )
    print_fields(grid)
    # ['OID', 'Shape', 'PageName', 'PageNumber']

    return grid


def split_islands_into_grid(borders, grid, output_to=None):
    """
    Given the buffer and a grid, get the intersection to create the fabled gridded_islands

    :param borders:
    :param grid:
    :param output_to:
    :return:
    """
    output_to = get_output_loc(output_to, 'split_islands')
    split_islands = Intersect_analysis([borders, grid], out_feature_class=output_to)
    print_fields(split_islands)
    # ['OBJECTID', 'Shape', 'FID_borders', 'FID_borders_tmp', 'Id', 'gridcode', 'BUFF_DIST', 'ORIG_FID', 'FID_roi', 'Id_1', 'FID_grid', 'PageName', 'PageNumber']

    return split_islands


def group_points_onto_islands(all_points, island_groups, output_to=None):
    output_to = get_output_loc(output_to, 'grouped_islands_points')
    island_points = Intersect_analysis(
        in_features=[all_points, island_groups],
        out_feature_class=output_to,
        join_attributes="ALL",
        output_type="POINT"
    )
    print_fields(island_points)

    return island_points


def create_high_point_table(spatial_reference):
    fp = CreateFeatureclass_management(
        'in_memory', 'final_points', 'POINT', has_z="ENABLED", spatial_reference=spatial_reference
    )

    AddField_management(fp, 'Z', field_type='INTEGER')
    AddField_management(fp, 'FID_island', field_type='LONG')
    AddField_management(fp, 'FID_split', field_type='LONG')
    AddField_management(fp, 'FID_grid', field_type='LONG')

    print_fields(fp)

    return fp


def generate_points_from_raster(raster, output_to=None, overwrite_existing=False):
    """

    :param raster:
    :param output_to:
    :return: ['OID', 'Shape', 'PointCount']
    """
    output_to = get_output_loc(output_to, 'islands_points')
    if Exists(output_to) and not overwrite_existing:
        return output_to
    all_points = RasterToMultipoint_3d(
        in_raster=raster,
        out_feature_class=output_to,
        method='NO_THIN',
        kernel_method='MAX'
    )
    print_fields(all_points)

    return all_points


def get_highest_points_from_multipoint_features(island_points, spatial_reference):
    """

    :param island_points: []
    :param spatial_reference:
    :return:
    """
    arcpy.AddMessage("island_points {}".format([x.name for x in arcpy.ListFields(island_points)]))

    highest = {}
    fp = create_high_point_table(spatial_reference)
    sc = InsertCursor(fp, ['SHAPE@', 'Z', 'FID_island', 'FID_split', 'FID_grid'])
    for i, (view_points, island, split, grid) in enumerate(
        SearchCursor(island_points, ["SHAPE@", 'Id', "FID_split_", 'PageNumber'])):

        candidate_point = highest.get(split, (None,))[0]
        for point in view_points:
            if candidate_point is None:
                candidate_point = point
            else:
                if point.Z > candidate_point.Z:
                    candidate_point = point
        highest[split] = (candidate_point, candidate_point.Z, island - 1, split - 1, grid - 1)

    for row in highest.itervalues():
        sc.insertRow(row)
    return fp


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
