from os.path import join, expanduser

import arcpy
import networkx as nx

arcpy.CheckOutExtension("Spatial")

workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', 'SL_Analysis', 'sl_-85')
arcpy.env.workspace = join(expanduser('~'), 'Documents', 'ARCS3001 PROJ', 'Scratch')
arcpy.env.overwriteOutput = True


def get_island_viewsheds():
    """
    :rtype: list[(int, int, float)]
    """
    # arcpy.Feature
    db = join(expanduser('~'), 'Documents', 'ArcGIS', 'Default.gdb')
    return arcpy.da.SearchCursor(join(db, "vs_intersect"), ["FID_islands", "FID_island", 'Shape_Area'])


def get_island(island_id):
    """
    :type island_id: int
    :rtype: (arcpy.Polygon, (int, int))
    """
    expr = '"FID" = {}'.format(island_id)
    return arcpy.da.SearchCursor(join(workspace, "islands.shp"), ["SHAPE@", "SHAPE@TRUECENTROID"],
                                 where_clause=expr).next()


def get_island_centroid(island_id):
    """
    :type island_id: int
    :rtype: list[(int, int)]
    """
    expr = '"FID" = {}'.format(island_id)
    return arcpy.da.SearchCursor(join(workspace, "islands.shp"), ["SHAPE@TRUECENTROID"], where_clause=expr).next()


if __name__ == '__main__':

    spatial_reference = arcpy.Describe(join(workspace, 'gridded_viewpoints.shp')).spatialReference

    d = nx.DiGraph()

    point = arcpy.Point()
    array = arcpy.Array()

    network = arcpy.CreateFeatureclass_management(
        workspace, "network7.shp", "POLYLINE", spatial_reference=spatial_reference
    )
    arcpy.AddField_management(network, 'island_A', field_type='LONG')
    arcpy.AddField_management(network, 'island_B', field_type='LONG')
    arcpy.AddField_management(network, 'A_sees_B', field_type='DOUBLE')

    cursor = arcpy.InsertCursor(network)
    feat = cursor.newRow()

    for i, (island_a_id, island_b_id, area) in enumerate(get_island_viewsheds()):
        if i % 100000 == 0:
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

    # print("Writing graph to file")
    # nx.write_gml(d, 'islands.gml')

    for (island_a_id, island_b_id, data) in d.edges_iter(data=True):
        for fid in [island_a_id, island_b_id]:
            expression = '"FID" = {}'.format(fid)
            ((island_b_x, island_b_y),) = arcpy.da.SearchCursor(join(workspace, "islands.shp"),
                                                                ["SHAPE@TRUECENTROID"],
                                                                where_clause=expression
                                                                ).next()
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
