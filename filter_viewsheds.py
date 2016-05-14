from collections import defaultdict
from os import mkdir, listdir
from os.path import join, exists, expanduser

import arcpy
from arcpy import env
from arcpy.da import InsertCursor, SearchCursor
from arcpy.sa import Con, Raster, ExtractByAttributes, BitwiseAnd
from math import ceil

from utils import get_field_names

arcpy.CheckOutExtension("Spatial")

workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', 'SL_Analysis', 'sl_-85')
env.workspace = workspace
env.overwriteOutput = True

viewpoints = join(workspace, "observer_points", "obs_points_0001.shp")
fieldnames = get_field_names(viewpoints)

viewshed_folder = join(workspace, 'individual_viewsheds')
for directory in [viewshed_folder]:
    if not exists(directory):
        mkdir(directory)

R = Raster(join(workspace, 'viewsheds', 'viewshed_0001'))

for i, row in enumerate(SearchCursor(viewpoints, ['FID_island', 'FID_point', 'observer'])):
    print(row)
    val = 1 if row[2] < 31 else -1
    extracted = Con(BitwiseAnd(R, (val << int(row[2]))), 1, None)
    extracted.save(join(viewshed_folder, 'i{:04d}_p{:05d}'.format(row[0], row[1])))
