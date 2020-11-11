import argparse

# Initialize parser
from pypads import logger

parser = argparse.ArgumentParser()

# Adding optional argument
parser.add_argument("-m", "--MongoDB", default="https://www.padre-lab.eu/onto/",
                    help="Set the url of the MongoDB.")
parser.add_argument("-m", "--MongoDBPassword", default="None",
                    help="Set the Password for the MongoDB.")

# Read arguments from command line
args, _ = parser.parse_known_args()

if args.OntologyUri:
    logger.info("Setting PyPads base ontology URI to: %s" % args.OntologyUri)

ontology_uri = args.OntologyUri
