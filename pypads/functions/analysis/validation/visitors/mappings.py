"""
The configuration-file 'mappings.json' is read during import of the module and stored statically inside the module.
"""

import importlib
import json
import os

import pip._internal.utils.misc as pip

type_mappings = {}
name_mappings = {}
alternate_name_mappings = {}
version_mappings = {}

path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../bindings/resources/mapping"))
mapping_files = os.listdir(path)

# For every file verify whether it is a json file and then add to the current type_mappings and name_mappings
for file in mapping_files:
    if os.path.isfile(os.path.join(path,file)) and file.endswith(".json"):
        try:
            with open(os.path.join(path,file), encoding='utf-8-sig') as f:
                data = json.loads(f.read())
                algorithms = data['algorithms']
                metadata = data['metadata']
                version_mappings[metadata['library']] = metadata

            for alg in algorithms:
                name_mappings[alg['name']] = alg

                for k in alg['implementation']:
                    type_mappings[alg['implementation'][k]] = (alg, k)

                for alt_name in alg['other_names']:
                    # Convert the alternate names to lower case for better usability
                    alternate_name_mappings[str(alt_name).lower()] = str(alg['name']).lower()

        except ValueError:
            raise ValueError('Error when parsing JSON file {name}'.format(name=file))

# Get all the packages
packages = pip.get_installed_distributions()

# Iterate through packages
for package in packages:
    if str(package).lower().startswith('pypa-'):
        package_name = str(package).lower().split(sep=' ')[0].replace('-', '_')
        module = importlib.import_module(package_name)
        if hasattr(module, 'get_mappings'):
            data = module.get_mappings()
            algorithms = data['algorithms']
            metadata = data['metadata']
            version_mappings[metadata['library']] = metadata
            for alg in algorithms:
                name_mappings[alg['name']] = alg

                for k in alg['implementation']:
                    type_mappings[alg['implementation'][k]] = (alg, k)

                for alt_name in alg['other_names']:
                    alternate_name_mappings[alt_name] = alg['name']


supported_frameworks = list(version_mappings.keys())
