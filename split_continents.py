from procedures.shape2table import poly_to_table
from procedures.viewshed import get_poly_rasters
from os.path import join, exists
import arcpy

# ws = r'C:\Users\kasih_000\Documents\Wallacea Viewshed\Scratch\SL_Analysis4\sl_-85'
ws = r'C:\Users\kasih_000\Documents\Wallacea Viewshed\Scratch\SL_Analysis4\sl_-85'
ws2 = r'C:\Users\kasih_000\Documents\DockerShared\out'

# MAIN_DB = "vs_anal5.gdb"
# SCRATCH = "scratch.gdb"
#
# ws3 = join(ws2, MAIN_DB)
# if not exists(ws3):
#     ws3 = arcpy.CreateFileGDB_management(ws2, MAIN_DB)
#
# scratch = join(ws2, SCRATCH)
# if not exists(scratch):
#     scratch = arcpy.CreateFileGDB_management(ws2, SCRATCH)
#
# print(ws2, scratch)

arcpy.env.workspace = ws2
# arcpy.env.scratchWorkspace = scratch
arcpy.env.overwriteOutput = True

arcpy.CheckOutExtension("Spatial")

if not arcpy.Exists('gridded_viewpoints'):
    viewpoints = arcpy.CopyFeatures_management(join(ws, 'gridded_viewpoints.shp'), 'gridded_viewpoints')
else:
    viewpoints = 'gridded_viewpoints'
spatial_reference = arcpy.Describe(viewpoints).spatialReference

poly_to_table(viewpoints, 'vs_polys7', spatial_reference)
