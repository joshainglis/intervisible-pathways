# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# wf1.py
# Created on: 2016-05-08 14:27:48.00000
#   (generated by ArcGIS/ModelBuilder)
# Description: 
# ---------------------------------------------------------------------------

# Import arcpy module
import arcpy


# Local variables:
rc_5 = "rc_5"
rc_5_ProjectRaster3_tif = "C:\\Users\\kasih_000\\Documents\\Wallacea Viewshed\\Scratch\\rc_5_ProjectRaster3.tif"
gridded_viewpoints = "SL+5\\gridded_viewpoints"
Viewshe_rc_51 = "C:\\Users\\kasih_000\\Documents\\Wallacea Viewshed\\Scratch\\Viewshe_rc_51"
Output_above_ground_level_raster = ""
gridded_viewpoints_Viewshed2_dbf = "C:\\Users\\kasih_000\\Documents\\Wallacea Viewshed\\Scratch\\gridded_viewpoints_Viewshed2.dbf"

# Process: Project Raster
arcpy.ProjectRaster_management(rc_5, rc_5_ProjectRaster3_tif,
                               "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],VERTCS['WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PARAMETER['Vertical_Shift',0.0],PARAMETER['Direction',1.0],UNIT['Meter',1.0]]",
                               "CUBIC", "rc_5", "", "",
                               "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]")

# Process: Viewshed 2
out_raster, out_agl_raster, out_observer_region_relationship_table = arcpy.Viewshed2_3d(
    in_raster=rc_5_ProjectRaster3_tif,
    in_observer_features=gridded_viewpoints,
    out_raster=Viewshe_rc_51,
    out_agl_raster=Output_above_ground_level_raster,
    analysis_type="OBSERVERS",
    vertical_error="0 Meters",
    out_observer_region_relationship_table=gridded_viewpoints_Viewshed2_dbf,
    refractivity_coefficient="0.13",
    surface_offset="0 Meters",
    observer_elevation="Z",
    observer_offset="5 Meters",
    inner_radius=None,
    inner_radius_is_3d="GROUND",
    outer_radius="300 Kilometers",
    outer_radius_is_3d="GROUND",
    horizontal_start_angle="0",
    horizontal_end_angle="360",
    vertical_upper_angle="90",
    vertical_lower_angle="-90",
    analysis_method="PERIMETER_SIGHTLINES"
)
