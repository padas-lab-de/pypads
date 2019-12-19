import click

from pypads.command.init import init
from pypads.command.remote import remote
from pypads.command.run import run


@click.group()
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    click.echo('Debug mode is %s' % ('on' if debug else 'off'))


@cli.command()
def cli_init():
    init()


@cli.command()
def cli_remote():
    remote()


@cli.command()
def cli_run():
    run()
