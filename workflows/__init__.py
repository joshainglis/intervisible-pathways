from arcpy import Describe

from procedures import create_island_inner_buffers, create_grid, split_islands_into_grid, group_points_onto_islands, \
    get_highest_points_from_multipoint_features
from procedures.viewshed import run_all_viewsheds
from utils import run_func


def run_full_analysis(sea_level, all_points, islands_poly, region_of_interest, distance_to_shore_meters, grid_width,
                      grid_height, dem, spatial_reference=None, save_intermediate=False, out_workspace=None,
                      overwrite_existing=False):
    if spatial_reference is None:
        spatial_reference = Describe(dem).spatialReference
    shared = dict(
        overwrite_existing=overwrite_existing,
        save_intermediate=save_intermediate,
        out_workspace=out_workspace
    )
    borders = run_func(
        save_loc='borders.shp',
        creation_message="Creating inner buffer zone of {}".format(distance_to_shore_meters),
        func=create_island_inner_buffers,
        args=(region_of_interest, islands_poly, distance_to_shore_meters),
        kwargs={},
        **shared
    )

    grid = run_func(
        save_loc='grid.shp',
        creation_message="Creating {} x {} grid over buffered area".format(grid_width, grid_height),
        func=create_grid,
        args=(borders,),
        kwargs=dict(grid_width=grid_width, grid_height=grid_height),
        **shared
    )

    split_islands = run_func(
        save_loc='split_islands.shp',
        creation_message="Splitting islands into grid",
        func=split_islands_into_grid,
        args=(borders, grid),
        kwargs={},
        **shared
    )

    island_points = run_func(
        save_loc='grouped_island_points.shp',
        creation_message="Grouping points for each island section",
        func=group_points_onto_islands,
        args=(all_points, split_islands),
        kwargs=dict(),
        **shared
    )

    viewpoints = run_func(
        save_loc='gridded_viewpoints.shp',
        creation_message="Getting highest point for each island section",
        func=get_highest_points_from_multipoint_features,
        args=(island_points, spatial_reference),
        kwargs=dict(),
        **shared
    )

    run_all_viewsheds(
        sea_level=sea_level,
        ws=out_workspace,
        viewpoints=viewpoints,
        dem=dem,
        overwrite_existing=overwrite_existing
    )
    return viewpoints
