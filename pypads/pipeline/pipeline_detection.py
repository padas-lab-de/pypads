import os
from logging import warning

import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log
from networkx import DiGraph
from networkx.drawing.nx_agraph import to_agraph

from pypads.autolog.wrapping import current_tracking_stack
from pypads.logging_util import WriteFormats, to_folder, try_write_artifact
from pypads.mlflow.mlflow_autolog import _is_package_available

last_pipeline_tracking = None

_pipeline_type = None
network = None

# --- Clean nodes after run ---
original_end = mlflow.end_run


def end_run(*args, **kwargs):
    global network
    if network is not None and len(network.nodes) > 0:
        try_write_artifact("_pypads_pipeline", network, WriteFormats.pickle)

        if _is_package_available("networkx"):
            base_folder = to_folder("")
            folder = base_folder + "pipeline_graph.png"
            if not os.path.exists(base_folder):
                os.mkdir(base_folder)
            if _is_package_available("agraph") and _is_package_available("graphviz"):
                if _pipeline_type == "simple":
                    agraph = to_agraph(DiGraph(network))
                elif _pipeline_type == "grouped":
                    copy = network.copy()
                    edge_groups = {}
                    for edge in copy.edges:
                        plain = copy.get_edge_data(*edge)['plain_label']
                        if plain not in edge_groups:
                            edge_groups[plain] = []
                        edge_groups[plain].append(edge)

                    for group, edges in edge_groups.items():
                        label = ""
                        suffix = ""
                        base_edge = None
                        for edge in edges:
                            splits = copy.get_edge_data(*edge)['label'].split(":")
                            if label == "":
                                label = splits[0]
                                suffix = splits[1]
                                base_edge = edge
                            else:
                                label = label + ", " + splits[0]
                            copy.remove_edge(*edge)
                        label = label + ":" + suffix
                        copy.add_edge(*base_edge, label=label)
                    agraph = to_agraph(copy)
                elif _pipeline_type == "grouped_no_count":
                    copy = network.copy()
                    edge_groups = {}
                    for edge in copy.edges:
                        plain = copy.get_edge_data(*edge)['plain_label']
                        if plain not in edge_groups:
                            edge_groups[plain] = edge

                    copy.remove_edges_from(network.edges())
                    for group, edge in edge_groups.items():
                        copy.add_edge(*edge, label=group)
                    agraph = to_agraph(copy)
                else:
                    agraph = to_agraph(network)
                agraph.layout('dot')
                agraph.draw(folder)
            elif _is_package_available("matplotlib"):
                import matplotlib.pyplot as plt
                import networkx as nx
                pos = nx.spring_layout(network)
                nx.draw(network, pos)
                nx.draw_networkx_labels(network, pos=pos)
                nx.draw_networkx_edge_labels(network, pos)
                plt.savefig(folder)
            try_mlflow_log(mlflow.log_artifact, folder)

    network = None
    global last_pipeline_tracking
    last_pipeline_tracking = None
    return original_end(*args, **kwargs)


mlflow.end_run = end_run


# !--- Clean nodes after run ---


def _to_node_id(mapping, ctx, wrappe, ref):
    if ref is not None:
        return id(ref)
    else:
        return id(wrappe)


def _to_label(mapping, ctx, wrappe, ref):
    if ref is not None:
        return str(ref)
    else:
        return str(wrappe)


def _step_number(label):
    return str(network.number_of_edges()) + ": " + label


def pipeline(self, *args, _pypads_autologgers=None, pipeline_type="normal", _pypads_wrappe, _pypads_context,
             _pypads_mapped_by,
             _pypads_callback, **kwargs):
    global last_pipeline_tracking
    global network
    global _pipeline_type
    _pipeline_type = pipeline_type

    if _is_package_available("networkx"):
        import networkx as nx
        if network is None:
            network = nx.MultiDiGraph()

        node_id = _to_node_id(_pypads_mapped_by, _pypads_context, _pypads_wrappe, self)
        label = _to_label(_pypads_mapped_by, _pypads_context, _pypads_wrappe, self)
        if not network.has_node(node_id):
            network.add_node(node_id, label=label)

        label = str(_pypads_wrappe)
        # If the current stack holds only the call itself
        if len(current_tracking_stack) == 1:

            # If there where no nodes until now
            if len(network.nodes) == 1:
                network.add_node(-1, label="entry")
                last_pipeline_tracking = -1
            network.add_edge(last_pipeline_tracking, node_id, plain_label=label, label=_step_number(label))

        # If the tracked function was called from another tracked function
        elif len(current_tracking_stack) > 1:

            containing_node_id = _to_node_id(*current_tracking_stack[-2])
            if not network.has_node(containing_node_id):
                containing_node_label = _to_label(*current_tracking_stack[-2])
                network.add_node(containing_node_id, label=containing_node_label)
            # Add an edge from the tracked function to the current function call
            network.add_edge(containing_node_id, node_id, plain_label=label, label=_step_number(label))

        output = _pypads_callback(*args, **kwargs)

        label = "return " + str(_pypads_wrappe)
        if len(current_tracking_stack) == 1:
            network.add_edge(node_id, -1, plain_label=label, label=_step_number(label))
        elif len(current_tracking_stack) > 1:
            containing_node_id = _to_node_id(*current_tracking_stack[-2])
            if not network.has_node(containing_node_id):
                containing_node_label = _to_label(*current_tracking_stack[-2])
                network.add_node(containing_node_id, label=containing_node_label)
            network.add_edge(node_id, containing_node_id, plain_label=label, label=_step_number(label))
    else:
        warning("Pipeline tracking currently needs networkx")
        output = _pypads_callback(*args, **kwargs)

    return output
