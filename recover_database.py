import arcpy
from os.path import join, expanduser

geodatabase = join(expanduser('~'), 'Documents', 'ArcGIS', 'recoveredDefault.gdb')
output_location = join(expanduser('~'), 'Documents', 'ArcGIS')
recovered_name = "recoveredDefault2.gdb"

arcpy.RecoverFileGDB_management(geodatabase, output_location, recovered_name)
