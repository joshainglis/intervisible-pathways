# Name: ExtractByRectangle_Ex_02.py
# Description:
# Requirements: Spatial Analyst Extension

# Import system modules
from genericpath import isdir
from os import mkdir
import time
import arcpy
from arcpy import env
from arcpy.sa import *

# Set environment settings
from os.path import expanduser, join

print "initialising"
workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch')
env.workspace = workspace
env.overwriteOutput = True

print "checking out extensions"
# Check out the ArcGIS Spatial Analyst extension license
arcpy.CheckOutExtension("Spatial")
arcpy.CheckOutExtension("3D")

time_outer = time.time()
try:
    print "loading gebco to memory",
    time_start = time.time()
    sea_level = -120
    inRaster = join("RN-9518_1450315858519", "GEBCO2014_89.7436_-24.0385_163.4615_30.1923_30Sec_ESRIASCII.asc")
    big_raster = arcpy.CopyRaster_management(inRaster, join('in_memory', 'big_raster'))
    r = Raster(big_raster)
    print time.time() - time_start

    print "creating sea level raster",
    time_start = time.time()
    sea_level_raster = Con(r <= sea_level, sea_level, r)
    print time.time() - time_start

    print "deleting viewshed_points.shp",
    time_start = time.time()
    arcpy.Delete_management(join(workspace, 'viewshed_points.shp'))
    print time.time() - time_start

    print "running analysis..."
    points = []
    # arcpy.Intersect_analysis(['gridIndexFeatures_50.shp', 'islands.shp'], out_feature_class='split_islands.shp')
    rows = (row.shape for row in arcpy.SearchCursor('split_islands.shp'))
    for i, polygon in enumerate(rows):
        time_loop_start = time.time()

        if i > 10:
            break
        print i, "extracting...",
        time_start = time.time()
        area = ExtractByRectangle(sea_level_raster, polygon.extent)  # type: arcpy.Raster
        print time.time() - time_start

        # area.save(join(workspace, 'area_{:04d}'.format(i)))
        print i, "getting max",
        time_start = time.time()
        max_height = area.maximum
        print time.time() - time_start

        # Contour(area, 'contour_grid_{:04d}'.format(i), 10)

        print i, "getting highest point raster",
        time_start = time.time()
        highest_point_raster = Con(area == max_height, max_height, 0)  # type: arcpy.Raster
        print time.time() - time_start

        print i, "setting null",
        time_start = time.time()
        highest_point_raster = SetNull(highest_point_raster, highest_point_raster, "VALUE = 0")  # type: arcpy.Raster
        print time.time() - time_start

        print i, "converting to point",
        time_start = time.time()
        point = arcpy.RasterToMultipoint_3d(
            highest_point_raster,
            out_feature_class=join('in_memory', 'height_point_{}'.format(i)),
            method='NO_THIN',
            kernel_method='MAX'
        )  # type: arcpy.Point
        print time.time() - time_start

        print i, "adding point",
        time_start = time.time()
        points.append(point)
        print time.time() - time_start

        print i, "Done", time.time() - time_loop_start, "\n"

    print "merging"
    viewshed_points = arcpy.Merge_management(points, join(workspace, 'viewshed_points.shp'))

finally:
    arcpy.Delete_management('in_memory')
    print "Done!", time.time() - time_outer
