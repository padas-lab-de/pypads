import argparse
import ast
import configparser

# Initialize parser
import os
from os.path import expanduser
from pypads import logger

# Configure
from pypads.variables import MLFLOW_TRACKING_URI, MLFLOW_S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, \
    MONGO_DB, MONGO_PW, DEFAULT_PYPADS, MONGO_URL, MONGO_USER, CONFIG


def parse_configfile(path, parsed_args):
    """
    Function that parse passed argument and configure default env varialbles.
    """
    config = configparser.ConfigParser()
    config.read(path)

    DEFAULTS = config[DEFAULT_PYPADS] if DEFAULT_PYPADS in config else {}

    # MLflow & Mongo DB related env variables
    pypads_envs = {MLFLOW_TRACKING_URI: parsed_args.uri,
                   MLFLOW_S3_ENDPOINT_URL: parsed_args.MLFLOW_S3_ENDPOINT_URL,
                   AWS_ACCESS_KEY_ID: parsed_args.AWS_ACCESS_KEY_ID,
                   AWS_SECRET_ACCESS_KEY: parsed_args.AWS_SECRET_ACCESS_KEY, MONGO_URL: parsed_args.MONGO_URL,
                   MONGO_DB: parsed_args.MONGO_DB, MONGO_USER: parsed_args.MONGO_USER,
                   MONGO_PW: parsed_args.MONGO_PW}

    # Set the env variables
    for k, v in pypads_envs.items():
        if v is None:
            if k in DEFAULTS.keys():
                os.environ[k] = DEFAULTS[k]
        else:
            os.environ[k] = v

    _CONFIG = config[CONFIG] if CONFIG in config else {}
    PYPADS_CONFIG = {}
    for key in _CONFIG:
        try:
            PYPADS_CONFIG[key] = ast.literal_eval(_CONFIG[key])
        except ValueError as e:
            PYPADS_CONFIG[key] = _CONFIG[key]
            logger.warning("Parsing datatype of config entry {} failed, taking as a string instead...".format(key))

    return PYPADS_CONFIG


PYPADS_FOLDER = os.path.join(expanduser("~"), ".pypads")

parser = argparse.ArgumentParser()

# Adding optional argument
parser.add_argument("-c", "--config", default=os.path.join(PYPADS_FOLDER, ".config"),
                    help="Path to a config file.")
parser.add_argument("-u", "--uri", default=None,
                    help="Set the tracking uri of your backend.")
parser.add_argument("-f", "--folder", default=PYPADS_FOLDER,
                    help="Set the path to the pypads folder.")
parser.add_argument("--MLFLOW_S3_ENDPOINT_URL", default=None,
                    help="Set the url of the S3 store endpoint of the tracking server.")
parser.add_argument("--AWS_ACCESS_KEY_ID", default=None,
                    help="Set Access Key Id for the AWS S3 bucket.")
parser.add_argument("--AWS_SECRET_ACCESS_KEY", default=None,
                    help="Set Secret Access Key for the AWS S3 bucket.")
parser.add_argument("--MONGO_URL", default=None,
                    help="Set the url of the MongoDB.")
parser.add_argument("--MONGO_DB", default=None,
                    help="Set the db name of the MongoDB.")
parser.add_argument("--MONGO_USER", default=None,
                    help="Set the user name for the MongoDB Access.")
parser.add_argument("--MONGO_PW", default=None,
                    help="Set the Password for the MongoDB Access.")

# Read arguments from command line
args, _ = parser.parse_known_args()
config_file = args.config
PYPADS_FOLDER = args.folder

PARSED_CONFIG = parse_configfile(config_file, args)

PYPADS_URI = args.uri or os.environ.get('MLFLOW_TRACKING_URI') or os.environ.get('MLFLOW_PATH') or os.path.join(
    PYPADS_FOLDER, ".mlruns")
