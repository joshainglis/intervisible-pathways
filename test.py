import time

# __author__ = 'kasih_000'
#
import arcpy
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
import numpy
import os
#
# cell_size_x = 0.00249998350695669
# cell_size_y = 0.00249994820000582
# nx = 7000
# ny = 7000
# no_data = -32768
# bottom = -17.349876
# left = 123.500199
# bottom_left = arcpy.Point(left, bottom)
# raster_loc = os.path.expanduser(os.path.join('~', 'Documents', 'ARCS3001 PROJ', 'Scratch'))
# out_loc = os.path.expanduser(os.path.join('~', 'Documents', 'DEM_mods'))
#
# data = arcpy.RasterToNumPyArray(os.path.join(raster_loc, "Extract_ausb1"),
#                                 lower_left_corner=bottom_left,
#                                 ncols=nx,
#                                 nrows=ny,
# )
#
# print(data.dtype)
#
# # valid = numpy.where(data != no_data)
# # data = data[valid[0][0]:valid[0][-1], valid[1][0]:valid[1][-1]]
#
#
# def infill(arr, reduction, min_height=0):
#     """
#     Con(
#         "Extract_DEMs4" <=  0,
#         "Extract_DEMs4" - 12,
#         Con(
#             "Extract_DEMs4" <= 12,
#             "Extract_DEMs4" - ( 1 * "Extract_DEMs4" * ( 1 - ( "Extract_DEMs4" / 12.0)) + 6.0) * 2,
#             "Extract_DEMs4"
#         )
#     )
#     """
#     a = arr.copy().astype(numpy.int16)
#     low = ((a <= min_height) & (a > no_data))
#     affected = ((a > min_height) & (a <= reduction))
#     a[low] -= reduction
#     a[affected] -= numpy.round((a[affected] * (1.0 - (a[affected] / float(reduction))) + reduction / 2.0) * 2).astype(numpy.int16)
#     return a
#
# print(numpy.median(data-infill(data, 12)))

# for red in xrange(1, 12):
#     print(red)
#     try:
#         tmp = infill(data, red)
#         arcpy.NumPyArrayToRaster(infill(data, red),
#                                  lower_left_corner=bottom_left,
#                                  x_cell_size=cell_size_x,
#                                  y_cell_size=cell_size_y,
#                                  value_to_nodata=no_data)\
#             .save(os.path.join(out_loc, "bath_blue_{0:02d}".format(red)))
#     except:
#         print('Error occured on red={}'.format(red))
#     finally:
#         del tmp
#


for x in xrange(1, 13):
    print 'Con("rastercalc192" <= 0, "rastercalc192" - {0}, Con("rastercalc192" <= {0}, ("rastercalc192" - (1 * "rastercalc192" * (1 - ( "rastercalc192" / {0})) + ({0}/2))) * 2, "rastercalc192"))'.format(x)

Con("rastercalc192" <= 0, "rastercalc192" - 4, Con("rastercalc192" <= 4, ("rastercalc192" - (1 * "rastercalc192" * (1 - ( "rastercalc192" / 4)) + (4/2))) * 2, "rastercalc192"))

Con("dems_joined" <= 0, "dems_joined" - 12, Con("dems_joined" <= 12, ("dems_joined" - (1 * "dems_joined" * (1 - ( "dems_joined" / 12)) + (12/2))) * 2, "dems_joined"))