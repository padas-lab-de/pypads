
from sklearn.pipeline import Pipeline

from pypads.autolog.visitors.experimentschema import default_pipeline_schema
from pypads.autolog.visitors.generalvisitor import generalize_visitor
from pypads.autolog.visitors.visitor import ListVisitor, AlgorithmVisitor, SubpathVisitor, SelectVisitor

SciKitPipelineVisitor = {
                "steps":
                    ListVisitor("steps",
                                (
                                              None,
                                              generalize_visitor(AlgorithmVisitor())
                                          )
                                ),
                "__doc__":
                    "doc"
            }

default_selector = {
    "sklearn.pipeline.Pipeline": SciKitPipelineVisitor,
    None: SubpathVisitor("steps[]", generalize_visitor(AlgorithmVisitor()))
}

default_visitor = SelectVisitor(default_selector, default_pipeline_schema)
