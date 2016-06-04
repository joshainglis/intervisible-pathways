from arcgisscripting import Raster

import arcpy
from arcpy import Exists, Buffer_analysis, Intersect_analysis, GridIndexFeatures_cartography, \
    RasterToPolygon_conversion, RasterToMultipoint_3d, CreateFeatureclass_management, AddField_management
from arcpy.da import InsertCursor, SearchCursor
from arcpy.sa import Con

from utils import get_output_loc, print_fields, in_mem


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
