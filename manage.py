#!/usr/bin/env python3
import os
import subprocess
import click
from flask.cli import FlaskGroup
from app import create_app

cli = FlaskGroup(create_app=create_app)


@cli.command('translate')
@click.option('--extract', is_flag=True, help='Extract messages from source')
@click.option('--update', is_flag=True, help='Update .po files from template')
def translate_cmd(extract, update):
    basedir = os.path.abspath(os.path.dirname(__file__))
    babel_cfg = os.path.join(basedir, 'babel.cfg')
    pot = os.path.join(basedir, 'messages.pot')
    translations = os.path.join(basedir, 'app', 'translations')

    if extract:
        click.echo('Extracting messages...')
        subprocess.run(['pybabel', 'extract', '-F', babel_cfg, '-o', pot, basedir], check=True)

    if update:
        if not os.path.exists(pot):
            click.echo('No messages.pot found. Run with --extract first.')
            return
        for lang in ['el', 'en']:
            click.echo(f'Updating {lang}...')
            subprocess.run(['pybabel', 'update', '-i', pot, '-d', translations, '-l', lang], check=True)

    click.echo('Compiling translations...')
    subprocess.run(['pybabel', 'compile', '-d', translations], check=True)
    if os.path.exists(pot) and not extract and not update:
        os.remove(pot)
    click.echo('Done.')


if __name__ == '__main__':
    cli()
