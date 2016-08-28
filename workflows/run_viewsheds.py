from os.path import join, expanduser

import arcpy
import click
from arcpy import env

from procedures.viewshed import run_all_viewsheds

arcpy.CheckOutExtension("Spatial")

workspace = join(expanduser('~'), 'Documents', 'Wallacea Viewshed', 'Scratch', 'SL_Analysis', 'sl_-85')
env.workspace = workspace
env.overwriteOutput = True


@click.command()
@click.option('--overwrite/--no-overwrite', default=False)
@click.option('--spatial-reference', '-s', default=None, type=str)
@click.argument('sea-level', type=int)
@click.argument('workspace',
                type=click.Path(exists=True, file_okay=True, dir_okay=True, resolve_path=True, writable=True))
@click.argument('viewpoints', type=click.STRING)
@click.argument('dem', type=click.STRING)
def run_viewsheds(sea_level, workspace, viewpoints, dem, spatial_reference, overwrite):
    run_all_viewsheds(sea_level, workspace, viewpoints, dem, spatial_reference, overwrite)


if __name__ == '__main__':
    run_viewsheds()
