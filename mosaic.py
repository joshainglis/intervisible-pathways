# Name: ExtractByRectangle_Ex_02.py
# Description:
# Requirements: Spatial Analyst Extension

# Import system modules
from genericpath import isdir
from os import mkdir

import arcpy
from arcpy import env
from arcpy.sa import *


# Set environment settings
from os.path import expanduser, join

workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', "UTM_Zones", "sea_levels")
env.workspace = workspace
env.overwriteOutput = True

# Check out the ArcGIS Spatial Analyst extension license
# arcpy.CheckOutExtension("Spatial")


utm_dir = join(workspace, "UTM_Zones")
utm_base_dir = join(utm_dir, "base")
utm_sea_level_dir = join(utm_dir, "sea_levels")


heights = range(-120, 6, 5)

for height in heights:
    out = 'sl_{}'.format(height)
    rasters = arcpy.ListRasters("*_{}".format(height), 'GRID')
    print rasters
    arcpy.CopyRaster_management(rasters[0], out)
    arcpy.Mosaic_management(inputs=rasters, target=out)
