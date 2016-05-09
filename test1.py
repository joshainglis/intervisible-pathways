# Replace a layer/table view name with a path to a dataset (which can be a layer file) or create the layer/table view within the script
# The following inputs are layers or table views: "UTM_52S_East\Ext_ET_adj_UTM.tif", "Babar_P_Z"
from os.path import join, expanduser

import arcpy
# arcpy.gp.Visibility_sa("UTM_52S_East/Ext_ET_adj_UTM.tif", "Babar_P_Z", "C:/Users/kasih_000/Documents/Wallacea Viewshed/Scratch/Vis2_Babar_P", "", "FREQUENCY", "ZERO", "1", "CURVED_EARTH", "0.13", "", "", "OFFSETA", "", "", "", "", "", "")

# Replace a layer/table view name with a path to a dataset (which can be a layer file) or create the layer/table view within the script
# The following inputs are layers or table views: "UTM_52S_East\Ext_ET_-69msl_UTM.tif", "P2_Z"
arcpy.CheckOutExtension("Spatial")
raster1 = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', "Ext_ET_adj_UTM.tif")
raster2 = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', "p2_z.shp")
# arcpy.gp.Visibility(
#     raster1, raster2, "C:/Users/kasih_000/Documents/Wallacea Viewshed/Scratch/Vis_P2", "", "FREQUENCY", "ZERO", "1", "CURVED_EARTH", "0.13", "", "", "OFFSETA", "", "", "", "", "", "")