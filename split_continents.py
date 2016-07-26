from procedures.viewshed import get_poly_rasters
from os.path import join
import arcpy

ws = r'C:\Users\kasih_000\Documents\Wallacea Viewshed\Scratch\SL_Analysis4\sl_-85'
arcpy.env.workspace = ws

arcpy.CheckOutExtension("Spatial")

viewpoints = join(ws, 'gridded_viewpoints.shp')
spatial_reference = arcpy.Describe(viewpoints).spatialReference

get_poly_rasters(viewpoints, ws, 'vs_polys3.shp', spatial_reference)
