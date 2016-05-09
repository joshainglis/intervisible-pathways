# Execute Visibility
from viewshed import visibility

outvis = visibility(
    in_raster="Ext_ET_adj_UTM.tif",
    in_observer_features="p2_z.shp",
    analysis_type="FREQUENCY",
    nonvisible_cell_value="ZERO",
    z_factor=1,
    curvature_correction="CURVED_EARTH",
    refractivity_coefficient=0.13,
    surface_offset=40,
)

# Save the output
outvis.save("C:/Users/kasih_000/Documents/Wallacea Viewshed/Scratch/Vis_P2_Python_2")
