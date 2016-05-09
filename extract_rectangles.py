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

workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch')
env.workspace = workspace
env.overwriteOutput = True

# Check out the ArcGIS Spatial Analyst extension license
arcpy.CheckOutExtension("Spatial")


# Set local variables
inRaster = join("RN-9518_1450315858519", "GEBCO2014_89.7436_-24.0385_163.4615_30.1923_30Sec_ESRIASCII.asc")
start_utm = 46
utm_width = 6
ymax = 30.19
ymin = -24.03
xmins = range(90, 156, utm_width)
sea_levels = range(-120, 6, 5)

utm_dir = join(workspace, "UTM_Zones")
utm_base_dir = join(utm_dir, "base")
utm_sea_level_dir = join(utm_dir, "sea_levels")
if not isdir(utm_dir):
    mkdir(utm_dir)
    mkdir(utm_base_dir)
    mkdir(utm_sea_level_dir)
for i, xmin in enumerate(xmins):
    utm = start_utm + i
    xmax = xmin + utm_width
    output_filename = join(utm_base_dir, "UTM_{}S".format(utm))

    print("Extracting UTM_{utm} with coords: (xmin={xmin}, ymin={ymin}, xmax={xmax}, ymax={ymax})".format(
        utm=utm, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax
    ))

    inRectangle = Extent(xmin, ymin, xmax, ymax)

    # Execute ExtractByRectangle
    rect_extract = ExtractByRectangle(inRaster, inRectangle, "INSIDE")
    print("Extraction Complete!")

    print("Converting to UTM zone {}".format(utm))
    arcpy.ProjectRaster_management(
        in_raster=rect_extract, out_raster=output_filename, out_coor_system=int("327{}".format(utm)))
    print("Conversion Complete!")

    for sea_level in sea_levels:
        print("Creating sea level raster for UTM_{} at with a sea level of {}m".format(utm, sea_level))
        r = Raster(output_filename)
        sea_level_raster = Con(r <= sea_level, sea_level, r)
        sea_level_raster.save(join(utm_sea_level_dir, "{}_{}".format(utm, sea_level)))
