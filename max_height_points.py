import sys
import arcpy
from arcpy import env
from arcpy.sa import *
from numpy import linspace

# Set environment settings
from os.path import expanduser, join

# workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', "UTM_Zones", "sea_levels")
print("setting up workspace")
workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch')
env.workspace = workspace
env.overwriteOutput = True

# Check out the ArcGIS Spatial Analyst extension license
print("checking out the spatial extension")
arcpy.CheckOutExtension("Spatial")

ymin = -24.03
ymax = 30.19
xmin = 90
xmax = 156

# print("Loading the DEM")
# inRaster = join("RN-9518_1450315858519", "GEBCO2014_89.7436_-24.0385_163.4615_30.1923_30Sec_ESRIASCII.asc")
# inRectangle = Extent(xmin, ymin, xmax, ymax)
#
# print("Extracting a section")
# rect_extract = ExtractByRectangle(inRaster, inRectangle, "INSIDE")
# rect_extract.save('ext_bath')


# print("Adding sea level")
# # raster = rect_extract
# raster = Raster('ext_bath')
# islands = raster > -120  # type: Raster
# islands = SetNull(islands, islands, "VALUE = 0")
# islands.save('islands')
#
# print("Creating polylines")
# arcpy.RasterToPolygon_conversion(islands, 'islands.shp')

print("Query rows")
rows = [row.shape for row in arcpy.SearchCursor('islands.shp')]  # type: list[arcpy.Polygon]
print len(rows)

roi = arcpy.SearchCursor('roi.shp').next().shape

print roi.extent
if not roi:
    sys.exit()
outers = []
km_100 = 50000 * 0.000009

for i, (poly, ) in enumerate(arcpy.da.SearchCursor('islands.shp', ['SHAPE@'])):
    print i
    if not roi.disjoint(poly):
        inner = poly.buffer(-km_100)
        outer = poly.difference(inner)
        outer = outer.intersect(roi, 4)
        outers.append(outer)

print "saving"
arcpy.FeatureClassToFeatureClass_conversion(outers, out_path=workspace, out_name='borders.shp')

print "Making the grid"
arcpy.GridIndexFeatures_cartography(
    out_feature_class="gridIndexFeatures_50",
    in_features='borders.shp',
    intersect_feature='INTERSECTFEATURE',
    polygon_width='30000 meters',
    polygon_height='30000 meters',
)

print('Done!')
