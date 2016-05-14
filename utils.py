from os.path import join, exists

import arcpy
from arcpy import CreateFeatureclass_management, AddField_management, RasterToPolygon_conversion, \
    FeatureClassToFeatureClass_conversion, GridIndexFeatures_cartography, Intersect_analysis, RasterToMultipoint_3d, \
    Describe, CopyFeatures_management
from arcpy import Point
from arcpy.da import InsertCursor, SearchCursor
from arcpy.sa import SetNull, Raster, ExtractByMask


def create_sea_level_island_polygons(base_raster, sea_level, output_to=None):
    if output_to is None:
        output_to = join('in_memory', 'islands')

    islands = Raster(base_raster) > sea_level  # type: Raster
    islands = SetNull(islands, islands, "VALUE = 0")
    islands_poly = RasterToPolygon_conversion(
        in_raster=islands,
        out_polygon_features=output_to,
    )
    return islands_poly


def meters_to_decimal_degrees(meters):
    return int(meters) * 0.000009


def create_island_inner_buffers(region_of_interest, islands_poly, distance_to_shore_meters):
    outers = []
    to_do = []

    for i, (poly,) in enumerate(SearchCursor(islands_poly, ['SHAPE@'])):
        if not region_of_interest.disjoint(poly):
            to_do.append(poly)
            inner = poly.buffer(-meters_to_decimal_degrees(distance_to_shore_meters))
            outer = poly.difference(inner)
            outer = outer.intersect(region_of_interest, 4)
            outers.append(outer)
    borders = FeatureClassToFeatureClass_conversion(
        outers, out_path='in_memory', out_name='borders'
    )
    return borders


def create_grid(in_features, grid_x_meters, grid_y_meters, output_to=None):
    if output_to is None:
        output_to = join('in_memory', 'grid')

    grid = GridIndexFeatures_cartography(
        out_feature_class=output_to,
        in_features=in_features,
        intersect_feature='INTERSECTFEATURE',
        polygon_width=grid_x_meters,
        polygon_height=grid_y_meters,
    )
    return grid


def split_islands_into_grid(borders, grid, output_to=None):
    if output_to is None:
        output_to = join('in_memory', 'split_islands')
    split_islands = Intersect_analysis([grid, borders], out_feature_class=output_to)
    return split_islands


def group_points_onto_islands(all_points, island_groups, output_to=None):
    if output_to is None:
        output_to = join('in_memory', 'grouped_islands_points')
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
    if output_to is None:
        output_to = join('in_memory', 'islands_points')

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
    for i, row in enumerate(
        SearchCursor(island_points, ["SHAPE@", 'FID_islands_points', "FID_split_islands", 'FID_grid'])):

        candidate_point = highest.get(row[2], (None,))[0]
        for p in row[0]:
            if candidate_point is None:
                candidate_point = p
            else:
                if p.Z > candidate_point.Z:
                    candidate_point = p
        highest[row[2]] = (candidate_point, candidate_point.Z, row[1], row[2], row[3])

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


def get_high_points(all_points, islands_poly, region_of_interest, distance_to_shore_meters, grid_x_meters,
                    grid_y_meters, spatial_reference=None, save_intermediate=False, out_workspace=None,
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

    grid = run_func(
        save_loc='grid',
        creation_message="Creating {} x {} grid over buffered area".format(grid_x_meters, grid_y_meters),
        func=create_grid,
        args=(borders,),
        kwargs=dict(grid_x_meters=grid_x_meters, grid_y_meters=grid_y_meters),
        **shared
    )

    split_islands = run_func(
        save_loc='split_islands',
        creation_message="Splitting islands into grid",
        func=split_islands_into_grid,
        args=(borders, grid),
        kwargs={},
        **shared
    )

    island_points = run_func(
        save_loc='grouped_island_points',
        creation_message="Grouping points for each island section",
        func=group_points_onto_islands,
        args=(all_points, split_islands),
        kwargs=dict(),
        **shared
    )

    viewpoints = run_func(
        save_loc='gridded_viewpoints',
        creation_message="Getting highest point for each island section",
        func=get_highest_points_from_multipoint_features,
        args=(island_points, spatial_reference),
        kwargs=dict(),
        **shared
    )
    return viewpoints


def get_field_names(shp):
    fieldnames = [f.name for f in arcpy.ListFields(shp)]
    return fieldnames
