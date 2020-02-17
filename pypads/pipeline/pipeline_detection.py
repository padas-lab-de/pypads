import mlflow

from pypads.autolog.wrapping import current_tracking_stack
from pypads.logging_util import try_write_artifact, WriteFormats

last_pipeline_tracking = None
nodes = []


class Node:

    def __init__(self, wrappe, ctx, ref):
        self._ref = str(ref)
        self._identity = id(ref)
        self._wrappe = str(wrappe)
        self._ctx = str(ctx)
        self._next = []
        self._previous = []
        self._parent = []
        self._child = []

    def add_next(self, node):
        self._next.append(node)

    def add_previous(self, node):
        self._previous.append(node)

    def add_parent(self, node):
        self._parent.append(node)

    def add_child(self, node):
        self._child.append(node)

    def is_entry(self):
        return len(self._previous) == 0 and len(self._parent) == 0


# --- Clean nodes after run ---
original_end = mlflow.end_run


def end_run(*args, **kwargs):
    try_write_artifact("_pypads_pipeline", nodes, WriteFormats.pickle)
    nodes.clear()
    global last_pipeline_tracking
    last_pipeline_tracking = None
    return original_end(*args, **kwargs)


mlflow.end_run = end_run


# !--- Clean nodes after run ---


def pipeline(self, *args, _pypads_autologgers=None, _pypads_wrappe, _pypads_context, _pypads_mapped_by,
             _pypads_callback, **kwargs):
    global last_pipeline_tracking
    node = None
    if len(current_tracking_stack) == 1:
        if len(nodes) == 0:
            node = Node(wrappe=_pypads_wrappe, ctx=_pypads_context, ref=self)
            nodes.append(node)
        else:
            node = Node(wrappe=_pypads_wrappe, ctx=_pypads_context, ref=self)
            node.add_previous(last_pipeline_tracking)
            last_pipeline_tracking.add_next(node)
            nodes.append(node)
    elif len(current_tracking_stack) > 1:
        node = Node(wrappe=_pypads_wrappe, ctx=_pypads_context, ref=self)
        node.add_parent(last_pipeline_tracking)
        last_pipeline_tracking.add_child(node)

    last_pipeline_tracking = node
    return _pypads_callback(*args, **kwargs)
