from os.path import join, expanduser

import arcpy
import networkx as nx

workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', 'SL_Analysis', 'sl_-85')
arcpy.env.overwriteOutput = True
spatial_reference = arcpy.Describe(join(workspace, 'gridded_viewpoints.shp')).spatialReference

# RUN = "20161015_200927"

OUTPUT_FOLDER = join(expanduser('~'), 'PycharmProjects', 'abm', 'output')

to_extract = [
    {
        'name': '20161218_115935',
        'scenarios': [
            {'name': 'all_demog', 'folder': 'north_demog', 'origins': ['north', 'south', 'taiwan', 'palawan']},
            {'name': 'north_demog', 'folder': 'north_demog', 'origins': ['north']},
            {'name': 'north_palawan_demog', 'folder': 'north_palawan_demog', 'origins': ['north', 'palawan']},
            {'name': 'palawan_demog', 'folder': 'palawan_demog', 'origins': ['palawan']},
            {'name': 'south_demog', 'folder': 'south_demog', 'origins': ['south']},
            {'name': 'south_north_demog', 'folder': 'south_north_demog', 'origins': ['south', 'north']},
            {'name': 'south_palawan_demog', 'folder': 'south_palawan_demog', 'origins': ['south', 'palawan']},
            {'name': 'taiwan_demog', 'folder': 'taiwan_demog', 'origins': ['taiwan']},
            {'name': 'taiwan_north_demog', 'folder': 'taiwan_north_demog', 'origins': ['taiwan', 'north']},
            {'name': 'taiwan_palawan_demog', 'folder': 'taiwan_palawan_demog', 'origins': ['taiwan', 'palawan']},
            {'name': 'taiwan_south_demog', 'folder': 'taiwan_south_demog', 'origins': ['taiwan', 'south']},
            {'name': 'north_oft', 'folder': 'north_oft', 'origins': ['north']},
            {'name': 'palawan_oft', 'folder': 'palawan_oft', 'origins': ['palawan']},
            {'name': 'south_oft', 'folder': 'south_oft', 'origins': ['south']},
            {'name': 'taiwan_oft', 'folder': 'taiwan_oft', 'origins': ['taiwan']},
        ]
    }
]

for run in to_extract:
    for scenario in run['scenarios']:
        d = nx.read_gpickle(join(OUTPUT_FOLDER, run['name'], scenario['folder'], 'traversal_path.gpickle'))
        for (island_a_id, island_b_id, data) in d.edges_iter(data=True):
            for origin in scenario['origins']:
                x = {
                    'traversals': 0,
                    'path': 0,
                    'tree': 0,
                }
                new = False
                for k in data:
                    if k.startswith(origin):
                        new = True
                        x['traversals'] += data[k]['traversals']
                        x['path'] += data[k]['path']
                        x['tree'] += data[k]['tree']
                if new:
                    data[origin] = x

        for origin in scenario['origins']:
            point = arcpy.Point()
            array = arcpy.Array()

            network = arcpy.CreateFeatureclass_management(
                workspace, "{}_{}_{}.shp".format(run['name'], scenario['name'], origin), "POLYLINE",
                spatial_reference=spatial_reference
            )
            arcpy.AddField_management(network, 'island_A', field_type='LONG')
            arcpy.AddField_management(network, 'island_B', field_type='LONG')
            arcpy.AddField_management(network, 'A_sees_B', field_type='DOUBLE')
            arcpy.AddField_management(network, 'travs', field_type='LONG')
            arcpy.AddField_management(network, 'paths', field_type='LONG')

            cursor = arcpy.da.InsertCursor(network, ["SHAPE@", "island_A", "island_B", "A_sees_B", "travs", 'paths'])

            for (island_a_id, island_b_id, data) in d.edges_iter(data=True):
                if origin not in data or 'traversals' not in data[origin]:
                    continue
                for fid in ['a', 'b']:
                    point.X = data[fid][0]
                    point.Y = data[fid][1]
                    array.add(point)
                polyline = arcpy.Polyline(array)
                array.removeAll()
                cursor.insertRow(
                    (
                        polyline, island_a_id, island_b_id, data['area'], data[origin]['traversals'],
                        data[origin]['path']))
            del cursor
