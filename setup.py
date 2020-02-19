# from sphinx.setup_command import BuildDoc
import re

from setuptools import setup, find_packages

# cmdclass = {'build_sphinx': BuildDoc}

NAMEFILE = "pypads/_name.py"
verstrline = open(NAMEFILE, "rt").read()
VSRE = r"^__name__ = ['\"]([^'\"]*)['\"]"
result = re.search(VSRE, verstrline, re.M)
if result:
    name = result.group(1)
else:
    raise RuntimeError("Unable to find name string in %s." % (NAMEFILE,))

VERSIONFILE = "pypads/_version.py"
verstrline = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
result = re.search(VSRE, verstrline, re.M)
if result:
    version = result.group(1)
    release = version
else:
    raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))

print('VERSION:{version}'.format(version=version))

with open('requirements.txt', 'r') as f:
    required = f.read()

with open('requirements-dev.txt', 'r') as f:
    dev_required = f.read()

install_requires = required
dev_requires = dev_required

setup(
    name=name,
    version=version,
    # TODO switch to scm version
    # use_scm_version=True,
    # setup_requires=['setuptools_scm'],
    packages=['pypads'] + find_packages(exclude=["tests", "tests.*", "*.tests.*", "*.tests"]),
    package_dir={'pypads': 'pypads'},
    include_package_data=True,
    url='https://padre-lab.eu',
    license='GPL',
    author='THomas Weißgerber',
    author_email='thomas.weissgerber@uni-passau.de',
    description='PyPaDS aims to solve problems about reproducibility',
    entry_points='''
       [console_scripts]
       pypads=pypads.cli.pypads:pypads
   ''',
    install_requires=install_requires,
    dev_requires=dev_requires,
    command_options={
        'build_sphinx': {
            'project': ('setup.py', name),
            'version': ('setup.py', version),
            'release': ('setup.py', release)}},
    # for click setup see http://click.pocoo.org/6/setuptools/
)

# todo add requirements txt for tests only
