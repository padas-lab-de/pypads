import os

import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads.autolog.wrapping import current_tracking_stack
from pypads.logging_util import WriteFormats, to_folder, try_write_artifact
from pypads.mlflow.mlflow_autolog import _is_package_available

last_pipeline_tracking = None
nodes = []


class Node:

    def __init__(self, wrappe, ctx, ref):
        self._ref = str(ref)
        self._identity = id(ref)
        self._wrappe = str(wrappe.__name__)
        self._ctx = str(ctx)
        self._next = []
        self._previous = []
        self._parent = None
        self._children = []

    @property
    def next(self):
        return self._next

    @property
    def previous(self):
        return self._previous

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        self._parent = parent

    @property
    def children(self):
        return self._children

    @property
    def wrappe(self):
        return self._wrappe

    @property
    def ctx(self):
        return self._ctx

    @property
    def identity(self):
        return self._identity

    @property
    def ref(self):
        return self._ref

    def add_next(self, node):
        self._next.append(node)

    def add_previous(self, node):
        self._previous.append(node)

    def add_child(self, node):
        self._children.append(node)

    def is_entry(self):
        return len(self._previous) == 0 and len(self._parent) == 0


# --- Clean nodes after run ---
original_end = mlflow.end_run


def end_run(*args, **kwargs):
    if len(nodes) > 0:
        try_write_artifact("_pypads_pipeline", nodes, WriteFormats.pickle)

        if _is_package_available("networkx") and _is_package_available("matplotlib"):
            import networkx as nx
            labels = {}
            edge_labels = {}
            graph = nx.DiGraph()
            for node in nodes:
                graph.add_node(node.identity)
                labels[node.identity] = node.ref
            for node in nodes:
                if len(node.next) > 0:
                    for next in node.next:
                        graph.add_edge(node.identity, next.identity)
                        edge_labels[node.identity, next.identity] = node.wrappe
                if len(node.children) > 0:
                    for child in node.children:
                        graph.add_edge(node.identity, child.identity)
                        edge_labels[node.identity, child.identity] = "_calls"

                if node.parent is not None:
                    graph.add_edge(node.identity, node.parent.identity)
                    edge_labels[node.identity, node.parent.identity] = node.wrappe

            import matplotlib.pyplot as plt

            pos = nx.spring_layout(graph)
            nx.draw(graph, pos)
            nx.draw_networkx_labels(graph, pos=pos, labels=labels)
            nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)
            base_folder = to_folder("")
            folder = base_folder + "pipeline_graph.png"
            if not os.path.exists(base_folder):
                os.mkdir(base_folder)
            plt.savefig(folder)
            try_mlflow_log(mlflow.log_artifact, folder)

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
        node.parent = last_pipeline_tracking
        last_pipeline_tracking.add_child(node)

    last_pipeline_tracking = node
    return _pypads_callback(*args, **kwargs)
