import re
from os import mkdir
from os.path import join, exists, expanduser, split

import arcpy
from arcpy import env

from utils import get_field_names

arcpy.CheckOutExtension("Spatial")

workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', 'SL_Analysis', 'sl_-85')
env.workspace = workspace
env.overwriteOutput = True

spatial_reference = arcpy.Describe(join(workspace, 'gridded_viewpoints.shp')).spatialReference

viewshed_folder = join(workspace, 'individual_viewsheds')
viewshed_polygon_folder = join(workspace, 'polygon_viewsheds')
for directory in [viewshed_folder, viewshed_polygon_folder]:
    if not exists(directory):
        mkdir(directory)

viewsheds = []
vs_poly_group = join(workspace, 'poly_layer.shp')
arcpy.Delete_management(vs_poly_group)
walk = arcpy.da.Walk(viewshed_folder, topdown=False, datatype="RasterDataset")

# fp = arcpy.CreateFeatureclass_management(
#     'in_memory', 'va_polygons', 'POLYGON', spatial_reference=spatial_reference
# )
#
# arcpy.AddField_management(fp, 'FID_split_', field_type='LONG')
viewshed_polys = join(workspace, 'viewshed_polys.shp')
fp = arcpy.CopyFeatures_management(viewshed_polys, join('in_memory', 'va_polygons'))

ic = arcpy.da.InsertCursor(fp, ['SHAPE@', 'FID_split_'])

for dirpath, dirnames, filenames in walk:
    g = split(dirpath)[-1]
    if not re.match(r'\d{3}', g):
        continue
    i = 0
    g = int(g)
    if g < 105:
        continue
    for filename in filenames:
        vs = join(dirpath, filename)
        print(vs)
        m = re.match(r'v(?P<vs_group>\d{3})i(?P<island_split>\d{5})o(?P<vs_id>\d{2}).*', filename)
        group = int(m.group('vs_group'))
        island_section = int(m.group('island_split'))
        o = int(m.group('vs_id'))
        if g == 105 and o < 5:
            continue
        try:
            vs_poly = arcpy.RasterToPolygon_conversion(
                in_raster=vs,
                out_polygon_features=join('in_memory', 'vs_poly'),
            )
            for row in arcpy.da.SearchCursor(vs_poly, ['OID@', "SHAPE@"]):
                ic.insertRow((row[1], island_section))
        except:
            print("Error while operating on {}".format(vs))
        i += 1
    print(int(arcpy.GetCount_management(fp).getOutput(0)))
arcpy.CopyFeatures_management(fp, 'viewshed_polys2')
