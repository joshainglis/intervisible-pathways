from abc import ABCMeta
from os import getenv


class EnvOverrideDefaults(type):
    __metaclass__ = ABCMeta

    def __new__(mcs, name, bases, attr_dict):
        for attr in [k for k in attr_dict if not k.startswith('_') and k.isupper]:
            attr_dict[attr] = getenv(attr, attr_dict[attr])
        return type.__new__(mcs, name, bases, attr_dict)


class TableNames(object):
    __metaclass__ = EnvOverrideDefaults

    IN_MEMORY = 'in_memory'

    FID = 'FID'
    ID = 'OID@'
    SHAPE = 'SHAPE@'
    CENTROID = "SHAPE@TRUECENTROID"

    ISLAND_ID = 'FID_island'
    SPLIT_ISLAND_ID = 'FID_split'
    ISLAND_GRID_ID = 'FID_grid'
    VIEWPOINT_ID = 'FID_point'
    OBSERVER = 'observer'

    INTERSECTED_ISLAND_ID = 'FID_islands'

    SHAPE_AREA = 'Shape_Area'

    Z = 'Z'

    A = 'island_A'
    B = 'island_B'
    A2B = 'A_sees_B'


class SaveLocations(object):
    __metaclass__ = EnvOverrideDefaults

    INDIVIDUAL_VIEWSHED_POLYGON_SAVE_LOCATION = \
        r'viewshed_{viewshed_number:04d}\viewshed_{viewshed_number:04d}_{viewshed_index:04d}.shp'

    @classmethod
    def individual_viewshed_polygon_save_location(cls, viewshed_number, viewshed_index):
        """
        :type viewshed_number: int
        :type viewshed_index: int
        :rtype: str
        """
        return cls.INDIVIDUAL_VIEWSHED_POLYGON_SAVE_LOCATION.format(
            viewshed_number=viewshed_number,
            viewshed_index=viewshed_index
        )

    FOLDER_VIEWSHEDS = 'viewsheds'
    FOLDER_TMP_OBSERVERS = 'observer_groups'
    FOLDER_OBSERVER_POINTS = 'observer_points'
