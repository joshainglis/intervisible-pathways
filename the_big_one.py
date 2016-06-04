"""
ArcGIS Module to select gridded highest points within a given area of the coast at various sea levels
"""
from arcgisscripting import ExecuteError
from os.path import join

# noinspection PyUnresolvedReferences
import arcpy
from arcpy import env, CheckOutExtension, GetParameterAsText, CopyFeatures_management, AddMessage
from procedures import create_sea_level_island_polygons
from procedures import generate_points_from_raster
from utils import create_dirs
from workflows import get_high_points

# Get CLI parameter values
workspace = GetParameterAsText(0)
dem = GetParameterAsText(1)
region_of_interest = GetParameterAsText(2)
distance_to_shore = GetParameterAsText(3)
low_sea_level = int(GetParameterAsText(4))
high_sea_level = int(GetParameterAsText(5))
sea_level_steps = int(GetParameterAsText(6))
grid_width = GetParameterAsText(7)
grid_height = GetParameterAsText(8)
save_intermediate = bool(eval(GetParameterAsText(9).title()))
out_workspace = GetParameterAsText(10)
overwrite_existing = bool(eval(GetParameterAsText(11).title()))

# workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch')
env.workspace = workspace
env.overwriteOutput = overwrite_existing

# Check out the ArcGIS 3D and Spatial Analyst extension licenses
CheckOutExtension("Spatial")
CheckOutExtension("3D")

# Create any directories that need creating
AddMessage("Setting up workspace")
create_dirs(out_workspace)

AddMessage("Generating points from raster (can take a long time!)")
all_points = generate_points_from_raster(dem, overwrite_existing=overwrite_existing)

for sea_level in range(low_sea_level, high_sea_level + 1, sea_level_steps):
    AddMessage("Sea Level {}".format(sea_level))

    wd = join(out_workspace, 'sl_{}'.format(sea_level))
    if save_intermediate:
        create_dirs(wd)

    kwargs = dict(save_intermediate=save_intermediate, out_workspace=wd, overwrite_existing=overwrite_existing)

    AddMessage("Generating Vector of islands at {}m".format(sea_level))
    islands_poly, existed = create_sea_level_island_polygons(dem, sea_level, overwrite_existing=overwrite_existing)

    if save_intermediate and not existed:
        save_to = join(wd, 'islands.shp')
        AddMessage("Saving Vector of islands to {}".format(save_to))
        try:
            CopyFeatures_management(islands_poly, save_to)
        except ExecuteError as e:
            if "ERROR 000725" not in e.message:
                raise e

    fp = get_high_points(sea_level, all_points, islands_poly, region_of_interest, distance_to_shore, grid_width,
                         grid_height,
                         dem, **kwargs)
