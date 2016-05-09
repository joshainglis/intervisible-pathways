# Name: Visibility_Ex_02.py
# Description: Determines the raster surface locations visible to a set of
#              observer features.
# Requirements: Spatial Analyst Extension

# Import system modules
import arcpy
from arcpy import env
# from numpy import array
# from arcpy.sa import *

# Set environment settings
from os.path import expanduser, join

env.workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch')


def visibility(
        in_raster,
        in_observer_features,
        out_agl_raster="#",
        analysis_type="#",
        nonvisible_cell_value="#",
        z_factor="#",
        curvature_correction="#",
        refractivity_coefficient="#",
        surface_offset="#",
        observer_elevation="#",
        observer_offset="#",
        inner_radius="#",
        outer_radius="#",
        horizontal_start_angle="#",
        horizontal_end_angle="#",
        vertical_upper_angle="#",
        vertical_lower_angle="#"):
    """Visibility(in_raster, in_observer_features, {out_agl_raster}, {analysis_type}, {nonvisible_cell_value}, {z_factor}, {curvature_correction}, {refractivity_coefficient}, {surface_offset}, {observer_elevation}, {observer_offset}, {inner_radius}, {outer_radius}, {horizontal_start_angle}, {horizontal_end_angle}, {vertical_upper_angle}, {vertical_lower_angle})

    Determines the raster surface locations visible to a set of observer features, or identifies which observer points are visible from each raster surface location.

    Results:
    out_raster -- Output raster
    :param in_raster: The input surface raster.
    :type in_raster: str
    :param in_observer_features: The feature class that identifies the observer locations.
    :type in_observer_features: str
    :param out_agl_raster: The output above-ground-level (AGL) raster.
    :type out_agl_raster: str
    :param analysis_type: The visibility analysis type.
    :type analysis_type: str
    :param nonvisible_cell_value: Value assigned to non-visible cells.
    :type nonvisible_cell_value: str
    :param z_factor: Number of ground x,y units in one surface z unit.
    :type z_factor: int | float
    :param curvature_correction: Allows correction for the earth's curvature.
    :type curvature_correction: str
    :param refractivity_coefficient: Coefficient of the refraction of visible light in air.
    :type refractivity_coefficient: float
    :param surface_offset: This value indicates a vertical distance (in surface units) to be added to the z-value of each cell as it is considered for visibility. It should be a positive integer or floating point value.
    :type surface_offset: float
    :param observer_elevation: This value is used to define the surface elevations of the observer points or vertices.
    :type observer_elevation: float
    :param observer_offset: This value indicates a vertical distance (in surface units) to be added to observer elevation. It should be a positive integer or floating point value.
    :type observer_offset: float
    :param inner_radius: This value defines the start distance from which visibility is determined. Cells closer than this distance are not visible in the output, but can still block visibility of the cells between inner radius and outer radius. It can be a positive or negative  integer or floating point value. If it is a positive value, then it is interpreted as three-dimensional, line-of-sight distance. If it is a negative value, then it is interpreted as  two-dimensional planimetric distance.
    :type inner_radius: float
    :param outer_radius: This value defines the maximum distance from which visibility is determined. Cells beyond this distance are excluded from the analysis. It can be a positive or negative  integer or floating point value. If it is a positive value, then it is interpreted as three-dimensional, line-of-sight distance. If it is a negative value, then it is interpreted as  two-dimensional planimetric distance.
    :type outer_radius: float
    :param horizontal_start_angle: This value defines the start angle of the horizontal scan range. The value should be specified in degrees from 0 to 360, with 0 oriented to north. The default value is 0.
    :type horizontal_start_angle: float
    :param horizontal_end_angle: This value defines the end angle of the horizontal scan range. The value should be specified in degrees from 0 to 360, with 0 oriented to north. The default value is 360.
    :type horizontal_end_angle: float
    :param vertical_upper_angle: This value defines the upper vertical angle limit of the scan above a horizontal plane. The value should be specified in degrees from 0 to 90, which can be integer or floating point.
    :type vertical_upper_angle: float
    :param vertical_lower_angle: This value defines the lower vertical angle limit of the scan below a horizontal plane. The value should be specified in degrees from -90 to 0, which can be integer or floating point.
    :type vertical_lower_angle: float
    :rtype: arcpy.Raster
    """

    arcpy.CheckOutExtension("Spatial")

    return arcpy.sa.Visibility(
        in_raster=in_raster,
        in_observer_features=in_observer_features,
        out_agl_raster=out_agl_raster,
        analysis_type=analysis_type,
        nonvisible_cell_value=nonvisible_cell_value,
        z_factor=z_factor,
        curvature_correction=curvature_correction,
        refractivity_coefficient=refractivity_coefficient,
        surface_offset=surface_offset,
        observer_elevation=observer_elevation,
        observer_offset=observer_offset,
        inner_radius=inner_radius,
        outer_radius=outer_radius,
        horizontal_start_angle=horizontal_start_angle,
        horizontal_end_angle=horizontal_end_angle,
        vertical_upper_angle=vertical_upper_angle,
        vertical_lower_angle=vertical_lower_angle
    )
