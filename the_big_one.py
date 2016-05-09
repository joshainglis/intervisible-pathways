from os import mkdir
from os.path import exists, join

import arcpy
from arcpy import env, CheckOutExtension, GetParameterAsText, Describe, CopyFeatures_management
from utils import create_sea_level_island_polygons, generate_points_from_raster, get_high_points

workspace = GetParameterAsText(0)
dem = GetParameterAsText(1)
region_of_interest = GetParameterAsText(2)
distance_to_shore_meters = GetParameterAsText(3)
low_sea_level = int(GetParameterAsText(4))
high_sea_level = int(GetParameterAsText(5))
sea_level_steps = int(GetParameterAsText(6))
grid_x_meters = GetParameterAsText(7)
grid_y_meters = GetParameterAsText(8)
save_intermediate = bool(eval(GetParameterAsText(9).title()))
out_workspace = GetParameterAsText(10)
overwrite_existing = bool(eval(GetParameterAsText(11).title()))

# workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch')
env.workspace = workspace
env.overwriteOutput = True

# Check out the ArcGIS 3D and Spatial Analyst extension licenses
CheckOutExtension("Spatial")
CheckOutExtension("3D")

arcpy.AddMessage("Setting up workspace")
if not exists(out_workspace):
    mkdir(out_workspace)

# raster = extract_region_of_interest(dem, region_of_interest)
arcpy.AddMessage("Extracting polygon from Region of Interest")
region_of_interest = arcpy.SearchCursor(region_of_interest).next().shape
spatial_reference = Describe(dem).spatialReference

arcpy.AddMessage("Generating points from raster (can take a long time!)")
all_points = generate_points_from_raster(dem)

for sea_level in range(low_sea_level, high_sea_level + 1, sea_level_steps):
    arcpy.AddMessage("Sea Level {}".format(sea_level))

    wd = join(out_workspace, 'sl_{}'.format(sea_level))
    if save_intermediate:
        if not exists(wd):
            arcpy.AddMessage("Creating {}".format(wd))
            mkdir(wd)

    arcpy.AddMessage("Generating Vector of islands at {}m".format(sea_level))
    islands_poly = create_sea_level_island_polygons(dem, sea_level)
    if save_intermediate:
        save_to = join(wd, 'islands')
        arcpy.AddMessage("Saving Vector of islands to {}".format(save_to))
        CopyFeatures_management(islands_poly, save_to)

    fp = get_high_points(all_points, islands_poly, region_of_interest, distance_to_shore_meters, grid_x_meters,
                         grid_y_meters, spatial_reference, save_intermediate=save_intermediate,
                         out_workspace=wd)

