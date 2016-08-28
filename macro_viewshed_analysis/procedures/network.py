import logging
from contextlib import contextmanager

import arcpy
import click
import networkx as nx

from macro_viewshed_analysis.config import TableNames as T
from macro_viewshed_analysis.utils import get_search_cursor, get_insert_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@contextmanager
def get_island_viewsheds(viewsheds_feature):
    """
    :type viewsheds_feature: str
    :rtype: collections.Iterable[(int, int, float)]
    """
    with get_search_cursor(viewsheds_feature, [T.ISLAND_ID, T.INTERSECTED_ISLAND_ID, T.SHAPE_AREA]) as sc:
        yield sc


def get_island(islands_feature, island_id, features=None):
    """
    :type islands_feature: str
    :type island_id: int
    :rtype: (arcpy.Polygon, (int, int))
    """
    if features is None:
        features = [T.SHAPE, T.CENTROID]
    expr = '{} = {}'.format(arcpy.AddFieldDelimiters(islands_feature, T.FID), island_id)
    with get_search_cursor(islands_feature, features, where_clause=expr) as islands_sc:
        return islands_sc.next()


def get_island_centroid(islands_feature, island_id):
    """
    :type islands_feature: str
    :type island_id: int
    :rtype: collections.Iterable[(int, int)]
    """
    return get_island(islands_feature, island_id, [T.CENTROID])


def get_viewshed_centroid(viewsheds_feature, island_a_id, island_b_id):
    """
    :type viewsheds_feature: str
    :type island_a_id: int
    :type island_b_id: int
    :rtype: collections.Iterable[(int, int)]
    """
    expr = '{} = {} AND {} = {}'.format(
        arcpy.AddFieldDelimiters(viewsheds_feature, T.ISLAND_ID), island_a_id,
        arcpy.AddFieldDelimiters(viewsheds_feature, T.INTERSECTED_ISLAND_ID), island_b_id
    )
    logger.debug(expr)
    with get_search_cursor(viewsheds_feature, [T.CENTROID], where_clause=expr) as sc:
        return sc.next()


def build_network(viewsheds_feature, islands_feature):
    """

    :type viewsheds_feature: str
    :type islands_feature: str
    :rtype: networkx.DiGraph
    """
    d = nx.DiGraph()

    with get_island_viewsheds(viewsheds_feature) as search_cursor:
        for i, (island_a_id, island_b_id, area) in enumerate(search_cursor):
            if i % 100000 == 0:
                logger.debug("Row: %d A: %d B: %d", i, island_a_id, island_b_id)
            if island_a_id != island_b_id:
                if island_a_id in d and island_b_id in d[island_a_id]:
                    d[island_a_id][island_b_id]['area'] += float(area)
                else:
                    try:
                        ((island_a_x, island_a_y),) = get_viewshed_centroid(islands_feature, island_b_id, island_a_id)
                    except StopIteration:
                        continue
                    try:
                        ((island_b_x, island_b_y),) = get_viewshed_centroid(islands_feature, island_a_id, island_b_id)
                    except StopIteration:
                        continue
                    d.add_edge(
                        island_a_id, island_b_id, {
                            'area': float(area),
                            'a': (island_a_x, island_a_y),
                            'b': (island_b_x, island_b_y)
                        }
                    )
    return d


def create_network_feature(workspace, output_name, islands_feature):
    """
    :type workspace: str
    :type output_name: str
    :type islands_feature: str
    :rtype: str
    """
    spatial_reference = arcpy.Describe(islands_feature).spatialReference
    network = arcpy.CreateFeatureclass_management(
        workspace, output_name, "POLYLINE", spatial_reference=spatial_reference
    )
    arcpy.AddField_management(network, T.A, field_type='LONG')
    arcpy.AddField_management(network, T.B, field_type='LONG')
    arcpy.AddField_management(network, T.A2B, field_type='DOUBLE')
    return network


def visualise_network(graph, workspace, output_name, islands_feature):
    """
    :type output_name: str
    :type islands_feature: str
    :type workspace: str
    :type graph: networkx.DiGraph
    :rtype: arcpy.FeatureSet
    """
    point = arcpy.Point()
    array = arcpy.Array()

    network = create_network_feature(workspace, output_name, islands_feature)

    with get_insert_cursor(network, [T.SHAPE, T.A, T.B, T.A2B]) as cursor:
        for (island_a_id, island_b_id, data) in graph.edges_iter(data=True):
            for fid in ['a', 'b']:
                point.X = data[fid][0]
                point.Y = data[fid][1]
                array.add(point)
            polyline = arcpy.Polyline(array)
            array.removeAll()
            cursor.insertRow((polyline, island_a_id, island_b_id, data['area']))
    return network


@click.command()
@click.option('--overwrite/--no-overwrite', default=False)
@click.argument('workspace',
                type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True, writable=True))
@click.argument('viewsheds', type=click.STRING)
@click.argument('islands', type=click.STRING)
@click.argument('out-file-name', type=click.STRING)
def build_and_output_network(workspace, viewsheds, islands, out_file_name, overwrite):
    arcpy.CheckOutExtension("Spatial")
    arcpy.env.workspace = workspace
    arcpy.env.overwriteOutput = overwrite

    g = build_network(viewsheds, islands)
    network = visualise_network(g, workspace, out_file_name, islands)
    logger.info("SUCCESS: output written to %s", network)


if __name__ == '__main__':
    build_and_output_network()
