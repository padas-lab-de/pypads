from .visitor import CombineVisitor

GeneralVisitor = {"__doc__": "doc"}


def generalize_visitor(visitor):
    """Add default fields to the visitor, e.g. the documentation. See GeneralVisitor"""
    return CombineVisitor([GeneralVisitor, visitor])
