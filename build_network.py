import logging
from os.path import join, expanduser

import arcpy
import networkx as nx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

arcpy.CheckOutExtension("Spatial")

workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', 'SL_Analysis', 'sl_-85')
arcpy.env.workspace = join(expanduser('~'), 'Documents', 'ARCS3001 PROJ', 'Scratch')
arcpy.env.overwriteOutput = True

db = join(expanduser('~'), 'Documents', 'Viewshed Analysis', 'vs_anal5.gdb')


def get_island_viewsheds():
    """
    :rtype: list[(int, int, float)]
    """
    # arcpy.Feature
    return arcpy.da.SearchCursor(join(db, "landmass_polys"),
                                 ["FID_island", "FID_islands", 'Shape_Area'])


def get_island(island_id):
    """
    :type island_id: int
    :rtype: (float, float, (float, float))
    """
    expr = '"FID" = {}'.format(island_id)
    return arcpy.da.SearchCursor(join(workspace, "islands.shp"), ["SHAPE@AREA", "SHAPE@LENGTH", "SHAPE@TRUECENTROID"],
                                 where_clause=expr).next()


def get_island_centroid(island_id):
    """
    :type island_id: int
    :rtype: list[(int, int)]
    """
    expr = '"FID" = {}'.format(island_id)
    return arcpy.da.SearchCursor(join(workspace, "islands.shp"), ["SHAPE@TRUECENTROID"], where_clause=expr).next()


def get_viewshed_centroid(island_a_id, island_b_id):
    """
    :type island_a_id: int
    :type island_b_id: int
    :rtype: list[(int, int)]
    """
    shp = join(db, "landmass_polys")
    expr = '{} = {} AND {} = {}'.format(
        arcpy.AddFieldDelimiters(shp, "FID_island"),
        island_a_id,
        arcpy.AddFieldDelimiters(shp, "FID_islands"),
        island_b_id
    )
    logger.debug(expr)
    return arcpy.da.SearchCursor(shp, ["SHAPE@TRUECENTROID"], where_clause=expr).next()


if __name__ == '__main__':
    d = nx.DiGraph()

    spatial_reference = arcpy.Describe(join(workspace, 'gridded_viewpoints.shp')).spatialReference

    point = arcpy.Point()
    array = arcpy.Array()

    network = arcpy.CreateFeatureclass_management(
        workspace, "network12.shp", "POLYLINE", spatial_reference=spatial_reference
    )
    arcpy.AddField_management(network, 'island_A', field_type='LONG')
    arcpy.AddField_management(network, 'island_B', field_type='LONG')
    arcpy.AddField_management(network, 'A_sees_B', field_type='DOUBLE')

    cursor = arcpy.InsertCursor(network)
    feat = cursor.newRow()

    for i, (island_a_id, island_b_id, area) in enumerate(get_island_viewsheds()):
        if i % 10000 == 0:
            print(i, island_a_id, island_b_id)
        if island_a_id != island_b_id:
            for island in (island_a_id, island_b_id):
                if island not in d:
                    island_area, island_perimeter, island_location = get_island(island)
                    d.add_node(island,
                               {'area': island_area, 'perimeter': island_perimeter, 'location': island_location})
            if island_a_id in d and island_b_id in d[island_a_id]:
                d[island_a_id][island_b_id]['area'] += float(area)
            else:
                try:
                    ((island_a_x, island_a_y),) = get_viewshed_centroid(island_b_id, island_a_id)
                except StopIteration:
                    continue
                    # ((island_a_x, island_a_y),) = get_island_centroid(island_a_id)
                try:
                    ((island_b_x, island_b_y),) = get_viewshed_centroid(island_a_id, island_b_id)
                except StopIteration:
                    continue
                    # ((island_b_x, island_b_y),) = get_island_centroid(island_b_id)
                d.add_edge(
                    island_a_id, island_b_id, {
                        'area': float(area),
                        'a': (island_a_x, island_a_y),
                        'b': (island_b_x, island_b_y)
                    }
                )

                # if 'pos' not in d.node[island_b_id]:
                #     try:
                #         ((island_b_x, island_b_y),) = get_viewshed_centroid(island_b_id, island_a_id)
                #     except StopIteration:
                #         ((island_b_x, island_b_y),) = get_island_centroid(island_b_id)
                #     d.node[island_b_id]['pos'] = {'x': island_b_x, 'y': island_b_y}
                # if 'pos' not in d.node[island_a_id]:
                #     try:
                #         ((island_a_x, island_a_y),) = get_viewshed_centroid(island_a_id, island_b_id)
                #     except StopIteration:
                #         ((island_a_x, island_a_y),) = get_island_centroid(island_a_id)
                #     d.node[island_a_id]['pos'] = {'x': island_a_x, 'y': island_a_y}

    print("Writing graph to file")
    nx.write_gpickle(d, 'islands.gpickle')
    # nx.write_weighted_edgelist(d, 'islands.gml')

    # for (island_a_id, island_b_id, data) in d.edges_iter(data=True):
    #     for fid in ['a', 'b']:
    #         point.X = data[fid][0]
    #         point.Y = data[fid][1]
    #         array.add(point)
    #     polyline = arcpy.Polyline(array)
    #     array.removeAll()
    #     # featureList.append(polyline)
    #     feat.shape = polyline
    #     feat.island_A = island_a_id
    #     feat.island_B = island_b_id
    #     feat.A_sees_B = data['area']
    #     cursor.insertRow(feat)
    del feat
    del cursor
