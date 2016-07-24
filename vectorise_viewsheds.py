import re
from os import mkdir
from os.path import join, exists, expanduser, split

import arcpy
from arcpy import env

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

# from collections import defaultdict
import networkx as nx

d = nx.DiGraph()
# d = defaultdict(set)

point = arcpy.Point()
array = arcpy.Array()

featureList = []

network = arcpy.CreateFeatureclass_management(
    arcpy.env.workspace, "network3.shp", "POLYLINE", spatial_reference=spatial_reference
)
arcpy.AddField_management(network, 'island_A', field_type='LONG')
arcpy.AddField_management(network, 'island_B', field_type='LONG')
arcpy.AddField_management(network, 'A_sees_B', field_type='LONG')

cursor = arcpy.InsertCursor(network)
feat = cursor.newRow()


def get_island_viewsheds():
    """
    :rtype: list[(int, int, float)]
    """
    return arcpy.da.SearchCursor("vs_intersect", ["FID_islands", "FID_island", 'Shape_Area'])


def get_island(island_id):
    """
    :type island_id: int
    :rtype: (arcpy.Polygon, (int, int))
    """
    expr = '"FID" = {}'.format(island_id)
    return arcpy.da.SearchCursor("islands", ["SHAPE@", "SHAPE@TRUECENTROID"], where_clause=expr).next()


def get_island_centroid(island_id):
    """
    :type island_id: int
    :rtype: list[(int, int)]
    """
    expr = '"FID" = {}'.format(island_id)
    return arcpy.da.SearchCursor("islands", ["SHAPE@TRUECENTROID"], where_clause=expr).next()


for i, (island_a_id, island_b_id, area) in enumerate(get_island_viewsheds()):
    if i % 10000 == 0:
        print(i, island_a_id, island_b_id)
    if island_a_id != island_b_id:
        if island_a_id in d and island_b_id in d[island_a_id]:
            d[island_a_id][island_b_id]['area'] += float(area)
        else:
            d.add_edge(island_a_id, island_b_id, {'area': float(area)})
        if 'pos' not in d.node[island_b_id]:
            ((island_b_x, island_b_y),) = get_island_centroid(island_b_id)
            d.node[island_b_id]['pos'] = {'x': island_b_x, 'y': island_b_y}
        if 'pos' not in d.node[island_a_id]:
            ((island_a_x, island_a_y),) = get_island_centroid(island_a_id)
            d.node[island_a_id]['pos'] = {'x': island_a_x, 'y': island_a_y}

    print("Writing graph to file")
    nx.write_gml(d, 'islands.gml')

for (island_a_id, island_b_id, data) in d.edges_iter(data=True):
    for fid in [island_a_id, island_b_id]:
        expression = '"FID" = {}'.format(fid)
        ((island_b_x, island_b_y),) = arcpy.da.SearchCursor("islands", ["SHAPE@TRUECENTROID"],
                                                            where_clause=expression).next()
        point.X = island_b_x
        point.Y = island_b_y
        array.add(point)
    polyline = arcpy.Polyline(array)
    array.removeAll()
    # featureList.append(polyline)
    feat.shape = polyline
    feat.island_A = island_a_id
    feat.island_B = island_b_id
    feat.A_sees_B = data['area']
    cursor.insertRow(feat)
del feat
del cursor
