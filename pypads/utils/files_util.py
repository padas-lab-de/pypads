# import json
# import os
# from glob import glob
#
# from pypads.utils.logging_util import read_artifact
# from pypads.utils.util import set_in_dict
#
#
# def find_directory(name, path):
#     """
#     Searches for a directory with the name starting from the path
#     :param name:
#     :param path:
#     :return: A list of directory paths
#     """
#     found_paths = []
#     for root, dirs, files in os.walk(path):
#         if name in dirs:
#             found_paths.append(os.path.join(root, name))
#
#     return found_paths
#
#
# def read_metric_file_contents(path):
#     """
#     Reads a ASCII text file and returns it as a list of tuples
#     :param path: Path for the file
#     :return: A list of tuples containing the timestamp, metric value and step number
#     """
#     result_tuple = []
#     with open(path, 'r') as fp:
#         content = fp.readlines()
#
#     for line in content:
#         result_tuple.append(tuple(line.strip().split(sep=' ')))
#
#     return result_tuple
#
#
# def get_metrics(root_path):
#     """
#     Reads all the files within the directories named metric
#     :param root_path: Root path from where the search begins
#     :return: Dictionary with the name of the metric as key and a list of tuples with timestamp, metric value and step
#     """
#
#     metrics_dict = dict()
#     metric_names = []
#     file_paths = []
#     paths = find_directory('metrics', root_path)
#     for path in paths:
#         file_names = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
#         metric_names = metric_names + file_names
#         file_paths = file_paths + [os.path.join(path, f) for f in file_names]
#
#     for idx, file in enumerate(file_paths):
#         result = read_metric_file_contents(file)
#         metrics_dict[metric_names[idx]] = result
#
#     return metrics_dict
#
#
# def get_params(root_path):
#     """
#     Finds all the parameters with the folder named params
#     :param root_path: Root path from where the search begins
#     :return: A nested dictionary with the key as the estimators and the second level containing individual parameters
#     """
#
#     params_dict = dict()
#     param_names = []
#     file_paths = []
#
#     # Find all subdirectories having the name param starting from the root path
#     paths = find_directory('params', root_path)
#     for path in paths:
#         file_names = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
#
#         # Add that to the file names
#         param_names = param_names + file_names
#         # Turn file names into absolute paths
#         file_paths = file_paths + [os.path.join(path, f) for f in file_names]
#
#     for idx, file_path in enumerate(file_paths):
#         param_dict = dict()
#         with open(file_path, "r") as fp:
#             content = fp.readline()
#         content = content.strip()
#         param_name = param_names[idx]
#         param = param_name.split(sep='.')[-1]
#         estimator = param_name[:param_name.rfind('.')]
#         param_dict[param] = content
#         existing_param_dict = params_dict.get(estimator, dict())
#         params_dict[estimator] = {**existing_param_dict, **param_dict}
#
#     return params_dict
#
#
# def get_tags(root_path):
#     """
#     Finds all the tags for an experimental run
#     :param root_path:
#     :return:
#     """
#     tags_dict = dict()
#     tag_names = []
#     file_paths = []
#     # Find all subdirectories having the name param starting from the root path
#     paths = find_directory('tags', root_path)
#     for path in paths:
#         file_names = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
#
#         # Add that to the file names
#         tag_names = tag_names + file_names
#         # Turn file names into absolute paths
#         file_paths = file_paths + [os.path.join(path, f) for f in file_names]
#
#     for idx, file_path in enumerate(file_paths):
#         with open(file_path, "r") as fp:
#             content = fp.readline()
#         content = content.strip()
#         tags_dict[tag_names[idx]] = content
#
#     return tags_dict
#
#
# def consolidate_run_output_files(root_path):
#     """
#     This function consolidates all the written JSON and text files for an experimental run
#     :param root_path: The path of the run from which the search begins
#     :return:
#     """
#
#     def read_file(path):
#         with open(path, 'r') as fp:
#             data = json.load(fp)
#         return data
#
#     consolidated_dict = dict()
#
#     # Find all the JSON files that will be concantenated by path
#     json_files = [y for x in os.walk(root_path) for y in glob(os.path.join(x[0], '*.json'))]
#     for json_file_path in json_files:
#         consolidated_dict[json_file_path] = read_file(json_file_path)
#
#     # Add the metrics
#     consolidated_dict['metrics'] = get_metrics(root_path=root_path)
#
#     # Add the parameters of the experiment
#     consolidated_dict['parameters'] = get_params(root_path=root_path)
#
#     # Add the tags of the experiment
#     consolidated_dict['tags'] = get_tags(root_path=root_path)
#
#     # Write the result
#     output_path = os.path.join(root_path, 'consolidated.json')
#     with open(output_path, "w") as fp:
#         fp.write(json.dumps(consolidated_dict))
#
#
# def get_paths(base_path, search: str = None):
#     """
#     Get all logged artifacts under base path filtered by search term if given.
#     :param base_path: base path for the lookup
#     :param search: search term to filter with
#     :return:
#     """
#     # TODO add a search filter.
#     import re
#     paths = []
#     for root, dirs, files in os.walk(base_path):
#         if search is not None:
#             matcher = re.compile(search)
#             for f in files:
#                 if matcher.search((os.path.join(root, f))):
#                     paths.append((os.path.join(root, f)))
#         else:
#             for f in files:
#                 paths.append(os.path.join(root, f))
#     return paths
#
#
# def get_artifacts(base_path, search: str = None):
#     """
#     Get all logged artifacts under base path filtered by search term if given.
#     :param base_path: base path for the lookup
#     :param search: search term to filter with
#     :return:
#     """
#     results = {"artifacts": dict()}
#     idx = len(base_path.split("/")) - 1
#     for root, dirs, files in os.walk(base_path):
#         keys = root.split('/')[idx:]
#         if search != "":
#             if search == keys[-1]:
#                 r = {f: read_artifact(os.path.join(root, f)) for f in files}
#                 set_in_dict(results, [keys[0], ".".join(keys[1:])], r)
#         else:
#             r = dict.fromkeys(dirs, dict())
#             set_in_dict(results, keys, r)
#             if files:
#                 r = {f: read_artifact(os.path.join(root, f)) for f in files}
#                 set_in_dict(results, keys, r)
#     return results
