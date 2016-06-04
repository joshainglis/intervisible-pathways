from os import mkdir
from os.path import join, exists

import arcpy
from arcpy import CreateFeatureclass_management, AddField_management, RasterToPolygon_conversion, \
    GridIndexFeatures_cartography, Intersect_analysis, RasterToMultipoint_3d, \
    Describe, CopyFeatures_management, Buffer_analysis, AddMessage
from arcpy import Point
from arcpy.da import InsertCursor, SearchCursor
from arcpy.sa import Raster, ExtractByMask, Con


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


def create_sea_level_island_polygons(base_raster, sea_level, output_to=None):
    """

    :param base_raster:
    :param sea_level:
    :param output_to:
    :return:
    """
    output_to = get_output_loc(output_to, 'islands')

    r = Raster(base_raster)
    islands = Con(r > sea_level, 1, None)  # type: Raster
    islands_poly = RasterToPolygon_conversion(
        in_raster=islands,
        out_polygon_features=output_to,
    )
    return islands_poly


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

    borders = Intersect_analysis([borders, region_of_interest], output_to)
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

    return split_islands


def group_points_onto_islands(all_points, island_groups, output_to=None):
    output_to = get_output_loc(output_to, 'grouped_islands_points')
    island_points = Intersect_analysis(
        in_features=[all_points, island_groups],
        out_feature_class=output_to,
        join_attributes="ALL",
        output_type="POINT"
    )
    return island_points


def create_high_point_table(spatial_reference):
    fp = CreateFeatureclass_management(
        'in_memory', 'final_points', 'POINT', has_z="ENABLED", spatial_reference=spatial_reference
    )

    AddField_management(fp, 'Z', field_type='INTEGER')
    AddField_management(fp, 'FID_island', field_type='LONG')
    AddField_management(fp, 'FID_split_', field_type='LONG')
    AddField_management(fp, 'FID_grid', field_type='LONG')
    return fp


def generate_points_from_raster(raster, output_to=None):
    output_to = get_output_loc(output_to, 'islands_points')

    all_points = RasterToMultipoint_3d(
        in_raster=raster,
        out_feature_class=output_to,
        method='NO_THIN',
        kernel_method='MAX'
    )  # type: Point

    return all_points


def get_highest_points_from_multipoint_features(island_points, spatial_reference):
    arcpy.AddMessage("island_points {}".format([x.name for x in arcpy.ListFields(island_points)]))

    highest = {}
    fp = create_high_point_table(spatial_reference)
    sc = InsertCursor(fp, ['SHAPE@', 'Z', 'FID_island', 'FID_split_', 'FID_grid'])
    for i, (view_points, points, split, grid) in enumerate(
        SearchCursor(island_points, ["SHAPE@", 'FID_islands_points', "FID_split_islands", 'FID_grid'])):

        candidate_point = highest.get(split, (None,))[0]
        for point in view_points:
            if candidate_point is None:
                candidate_point = point
            else:
                if point.Z > candidate_point.Z:
                    candidate_point = point
        highest[split] = (candidate_point, candidate_point.Z, points, split, grid)

    for row in highest.itervalues():
        sc.insertRow(row)
    return fp


def extract_region_of_interest(dem, region_of_interest):
    arcpy.AddMessage("Extracting ")
    (roi,) = SearchCursor(region_of_interest, ['SHAPE@']).next()
    rect_extract = ExtractByMask(dem, roi)
    raster = Raster(rect_extract)
    return raster


def run_func(overwrite_existing, out_workspace, save_loc, save_intermediate, creation_message, func, args, kwargs):
    save_to = join(out_workspace, save_loc)
    if not overwrite_existing:
        if exists(save_to):
            arcpy.AddMessage("Using existing file at {}".format(save_to))
            return save_to
    arcpy.AddMessage(creation_message)
    out_var = func(*args, **kwargs)
    if save_intermediate:
        arcpy.AddMessage("Saving {} to {}".format(save_loc, save_to))
        CopyFeatures_management(out_var, save_to)
    return out_var


def get_high_points(all_points, islands_poly, region_of_interest, distance_to_shore_meters, grid_width,
                    grid_height, spatial_reference=None, save_intermediate=False, out_workspace=None,
                    overwrite_existing=False):
    if spatial_reference is None:
        spatial_reference = Describe(islands_poly).spatialReference
    shared = dict(
        overwrite_existing=overwrite_existing,
        save_intermediate=save_intermediate,
        out_workspace=out_workspace
    )
    borders = run_func(
        save_loc='borders',
        creation_message="Creating inner buffer zone of {}".format(distance_to_shore_meters),
        func=create_island_inner_buffers,
        args=(region_of_interest, islands_poly, distance_to_shore_meters),
        kwargs={},
        **shared
    )
    print_fields(borders)

    grid = run_func(
        save_loc='grid',
        creation_message="Creating {} x {} grid over buffered area".format(grid_width, grid_height),
        func=create_grid,
        args=(borders,),
        kwargs=dict(grid_width=grid_width, grid_height=grid_height),
        **shared
    )
    print_fields(grid)

    split_islands = run_func(
        save_loc='split_islands',
        creation_message="Splitting islands into grid",
        func=split_islands_into_grid,
        args=(borders, grid),
        kwargs={},
        **shared
    )
    print_fields(split_islands)

    island_points = run_func(
        save_loc='grouped_island_points',
        creation_message="Grouping points for each island section",
        func=group_points_onto_islands,
        args=(all_points, split_islands),
        kwargs=dict(),
        **shared
    )
    print_fields(island_points)

    # viewpoints = run_func(
    #     save_loc='gridded_viewpoints',
    #     creation_message="Getting highest point for each island section",
    #     func=get_highest_points_from_multipoint_features,
    #     args=(island_points, spatial_reference),
    #     kwargs=dict(),
    #     **shared
    # )
    # return viewpoints
