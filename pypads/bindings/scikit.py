
from sklearn.pipeline import Pipeline

from pypads.autolog.visitors.experimentschema import PipelineSchema
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


SciKitSelector = {
    Pipeline: SciKitPipelineVisitor,
    None: SubpathVisitor("steps[]", generalize_visitor(AlgorithmVisitor()))
}


SciKitVisitor = SelectVisitor(SciKitSelector, PipelineSchema)
