import argparse

# Initialize parser
parser = argparse.ArgumentParser()

# Adding optional argument
parser.add_argument("-o", "--OntologyUri", default="https://www.padre-lab.eu/onto/",
                    help="Set the base URI for concepts defined in an ontology.")

# Read arguments from command line
args = parser.parse_args()

if args.OntologyUri:
    print("Setting PyPads base ontology URI to: %s" % args.OntologyUri)

ontology_uri = args.OntologyUri
