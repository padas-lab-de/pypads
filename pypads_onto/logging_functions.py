import copy

from pypads import logging_functions

original_log_init = logging_functions.log_init

from rdflib import Graph, Literal, BNode, Namespace
from rdflib.namespace import FOAF, RDFS, RDF, XSD

ML = Namespace('http://padim.uni-passau.de/ML#')
ml_tbox = '''
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix vann: <http://purl.org/vocab/vann/> .
@prefix void: <http://rdfs.org/ns/void#> .
@prefix vs: <http://www.w3.org/2003/06/sw-vocab-status/ns#> .
@prefix wot: <http://xmlns.com/wot/0.1/> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ml: <http://padim.uni-passau.de/ML#> .

ml:Estimator a rdfs:Class , owl:Class ; 
    rdfs:label "Estimator" ;
    rdfs:comment "Estimator that follows sklearn's estimator pattern" .

ml:HyperParameter a rdfs:Class, owl:Class;
    rdfs:label "Hyperparameter" .

ml:Task a rdfs:Class, owl:Class ;
    rdfs:label "Task" ;
    rdfs:comment "Machine Learning Task" .

ml:Metric a rdfs:Class, owl:Class;
    rdfs:label "Metric" ;
    rdfs:comment "Metric for evaluating Machine Learning tasks" .

ml:hasParameter a rdf:Property;
    rdfs:domain ml:Estimator;
    rdfs:range ml:HyperParameter.

ml:hasDefault a rdf:Property;
    rdfs:domain ml:HyperParameter.

ml:summary a rdf:Property;
    rdfs:domain ml:Estimator;
    rdfs:range xsd:string.

ml:extended_summary a rdf:Property;
    rdfs:domain ml:Estimator;
    rdfs:range xsd:string.

ml:references a rdf:Property;
    rdfs:domain ml:Estimator;
    rdfs:range xsd:string.

ml:solvesTask a rdf:Property;
    rdfs:domain ml:Estimator;
    rdfs:range ml:Task.

ml:evaluatesTaskSolution a rdf:Property;
    rdfs:domain ml:Metric;
    rdfs:range ml:Task.

ml:hasType a rdf:Property;
    rdfs:domain ml:HyperParameter.
'''

tbox_graph = Graph()
tbox_graph.parse(data=ml_tbox, format='n3')

type_mappings = {'string': XSD.string, 'integer': XSD.integer, 'boolean': XSD.boolean, 'float': XSD.float, }


def estimator_df_to_rdf(df, graph=None):
    def estimator_to_rdf(estimator, parameters, superclasses, methods, summary,
                         extended_summary, tasks, package, references=''):
        estimator_id = estimator.__name__
        estimator_node = BNode()  # estimator_id)
        graph.add((estimator_node, FOAF.name, Literal(estimator.__name__)))
        graph.add((estimator_node, RDF.type, ML.Estimator))
        graph.add((estimator_node, ML.summary, Literal(summary)))
        graph.add((estimator_node, ML.extendedSummary, Literal(extended_summary)))
        graph.add((estimator_node, ML.references, Literal(references)))

        for parameter_row in parameters.to_dict('rows'):
            parameter_node = BNode()  # estimator_id + '.' + parameter_row['name'])
            graph.add((parameter_node, RDF.type, ML.HyperParameter))
            graph.add((parameter_node, FOAF.name, Literal(parameter_row['name'])))
            graph.add((estimator_node, ML.hasParameter, parameter_node))
            graph.add((parameter_node, RDFS.comment, Literal(parameter_row['desc'])))
            graph.add((parameter_node, RDF.type, Literal(parameter_row['type'])))

            graph.add((parameter_node, ML.hasDefault, Literal(parameter_row['default'])))
        for task in tasks:
            task_node = BNode()  # task)
            graph.add((task_node, RDF.type, ML.Task))
            graph.add((estimator_node, ML.solvesTask, task_node))

    graph: Graph = Graph() if graph is None else copy.deepcopy(graph)

    for row in df.to_dict('rows'):
        params = [row[k] for k in ('cls', 'parameters', 'superclasses', 'methods', 'summary',
                                   'extended_summary', 'tasks', 'package', 'references')]
        estimator_to_rdf(*params)
    return graph


# TODO build ontology while executing?


def ontology(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by,
             _pypads_callback, **kwargs):
    """
        Function logging the loaded dataset.
        :param self: Wrapper library object
        :param args: Input args to the real library call
        :param _pypads_wrappe: _pypads provided - wrapped library object
        :param _pypads_mapped_by: _pypads provided - wrapped library package
        :param _pypads_item: _pypads provided - wrapped function name
        :param _pypads_fn_stack: _pypads provided - stack of all the next functions to execute
        :param kwargs: Input kwargs to the real library call
        :return:
        """
    import inspect
    if inspect.isclass(self):
        cls = self
    else:
        cls = self.__class__

    cls_doc = cls.__doc__

    result = original_log_init(self, *args, _pypads_wrappe=_pypads_wrappe, _pypads_context=_pypads_context,
                               _pypads_mapped_by=_pypads_mapped_by,
                               _pypads_callback=_pypads_callback, **kwargs)
    return result


logging_functions.log_init = ontology
