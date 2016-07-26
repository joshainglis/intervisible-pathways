from os import mkdir
from os.path import join, exists, expanduser

import arcpy
from arcpy import env
from arcpy.da import SearchCursor
from arcpy.sa import Con, Raster, BitwiseAnd

arcpy.CheckOutExtension("Spatial")

workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', 'SL_Analysis', 'sl_-85')
env.workspace = workspace
env.overwriteOutput = True

viewshed_folder = join(workspace, 'individual_viewsheds')
for directory in [viewshed_folder]:
    if not exists(directory):
        mkdir(directory)

for vs_num in range(105, 106):
    try:
        viewpoints = join(workspace, "tst_points_{:04d}.shp".format(vs_num))

        R = Raster(join(workspace, 'viewsheds', 'viewshed_{:04d}'.format(vs_num)))

        vs_dir = join(viewshed_folder, '{:03d}'.format(vs_num))
        if not exists(vs_dir):
            mkdir(vs_dir)

        for i, row in enumerate(SearchCursor(viewpoints, ['FID', 'FID_split_'])):
            try:
                print("{:03d}: {}".format(vs_num, row))
                val = 1 if row[0] < 31 else -1
                extracted = Con(BitwiseAnd(R, (val << int(row[0]))), 1, None)
                extracted.save(join(vs_dir, 'v{:03d}i{:05d}o{:02d}'.format(vs_num, row[1], row[0])))
            except Exception as e:
                print("Problem on {}-{}: {}".format(vs_num, i, e.message))

    except Exception as e:
        print("Problem on {}: {}".format(vs_num, e.message))
