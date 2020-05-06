import os

import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads import logger
from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.logging_util import WriteFormats, get_base_folder, try_write_artifact
from pypads.util import is_package_available


# last_pipeline_tracking = None
#
# _pipeline_type = None
# network = None


# --- Clean nodes after run ---
def end_run(pads, *args, **kwargs):
    # curr_call = pads.call_tracker.current_call()
    # Todo should we track the pipeline per process
    pipeline_cache = pads.cache.get("pipeline", {})

    network = pipeline_cache.get("network", None)
    _pipeline_type = pipeline_cache.get("pipeline_type")
    # global network
    if network is not None and len(network.nodes) > 0:
        from networkx import DiGraph
        from networkx.drawing.nx_agraph import to_agraph
        try_write_artifact("_pypads_pipeline", network, WriteFormats.pickle)

        if is_package_available("networkx"):
            base_folder = get_base_folder()
            folder = base_folder + "pipeline_graph.png"
            if not os.path.exists(base_folder):
                os.mkdir(base_folder)
            if is_package_available("agraph") and is_package_available("graphviz"):
                try:
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
                except ValueError as e:
                    logger.warning("Failed plotting pipeline: " + str(e))
            elif is_package_available("matplotlib"):
                import matplotlib.pyplot as plt
                import networkx as nx
                pos = nx.spring_layout(network)
                nx.draw(network, pos)
                nx.draw_networkx_labels(network, pos=pos)
                nx.draw_networkx_edge_labels(network, pos)
                plt.savefig(folder)
            if os.path.exists(folder):
                try_mlflow_log(mlflow.log_artifact, folder)

    pads.cache.pop("pipeline")
    # # global last_pipeline_tracking
    # # last_pipeline_tracking = None
    # pads.cache.pop(curr_call)


# !--- Clean nodes after run ---


def _to_node_id(wrappe, ref):
    if ref is not None:
        return id(ref)
    else:
        return id(wrappe)


def _to_node_label(wrappe, ref):
    if ref is not None:
        try:
            return str(ref)
        except Exception as e:
            try:
                logger.warning(
                    "Couldn't get str representation for given ref of type " + str(
                        type(ref)) + ". Falling back to " + str(
                        wrappe) + " and id or ref " + str(id(ref)) + ". " + str(e))
                return str(wrappe) + str(id(ref))
            except Exception as e:
                logger.warning("Couldn't get fallback string. Fallback to id " + str(id(ref)) + ". " + str(e))
                return str(id(ref))
    else:
        return str(wrappe)


def _to_edge_label(wrappe, include_args, args, kwargs):
    if include_args:
        return str(wrappe) + " args: " + str(args) + " kwargs: " + str(kwargs)
    return str(wrappe)


def _step_number(network, label):
    return str(network.number_of_edges()) + ": " + label


class PipelineTracker(LoggingFunction):

    def _needed_packages(self):
        return ["networkx"]

    def __pre__(self, ctx, *args, _pypads_env: LoggingEnv, _pypads_pipeline_type="normal", _pypads_pipeline_args=False,
                **kwargs):

        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        pads.api.register_post_fn("pipeline_clean_up", end_run)


        if pads.cache.exists("pipeline"):
            pipeline_cache = pads.cache.get("pipeline")
        else:
            pipeline_cache = {"network": None, "last_pipeline_tracking":None, "pipeline_type":_pypads_pipeline_type}

        network = pipeline_cache.get("network")
        last_pipeline_tracking = pipeline_cache.get("last_pipeline_tracking")
        _pipeline_type = pipeline_cache.get("pipeline_type")

        import networkx as nx
        if network is None:
            network = nx.MultiDiGraph()

        node_id = _to_node_id(_pypads_env.call.call_id.wrappee, ctx)
        label = _to_node_label(_pypads_env.call.call_id.wrappee, ctx)
        if not network.has_node(node_id):
            network.add_node(node_id, label=label)

        label = _to_edge_label(_pypads_env.call.call_id.wrappee, _pypads_pipeline_args, args, kwargs)
        # If the current stack holds only the call itself
        if pads.call_tracker.call_depth() == 1:

            # If there where no nodes until now
            if len(network.nodes) == 1:
                network.add_node(-1, label="entry")
                last_pipeline_tracking = -1
                pipeline_cache["last_pipeline_tracking"] = -1
            network.add_edge(last_pipeline_tracking, node_id, plain_label=label, label=_step_number(network,label))

        # If the tracked function was called from another tracked function
        elif pads.call_tracker.call_depth() > 1:

            containing_node_id = _to_node_id(pads.call_tracker.call_stack[-2].call_id.wrappee, ctx)
            if not network.has_node(containing_node_id):
                containing_node_label = _to_node_label(pads.call_tracker.call_stack[-2].call_id.wrappee, ctx)
                network.add_node(containing_node_id, label=containing_node_label)
            # Add an edge from the tracked function to the current function call
            network.add_edge(containing_node_id, node_id, plain_label=label, label=_step_number(network,label))

        pipeline_cache["network"] = network
        pads.cache.add("pipeline",pipeline_cache)
        return node_id

    def __post__(self, ctx, *args, _pypads_pipeline_args=False, _pypads_env: LoggingEnv, _pypads_pre_return, **kwargs):
        from pypads.pypads import get_current_pads
        pads = get_current_pads()

        pipeline_cache = pads.cache.get("pipeline")
        network = pipeline_cache.get("network")
        node_id = _pypads_pre_return
        label = "return " + _to_edge_label(_pypads_env.call.call_id.wrappee, _pypads_pipeline_args, args, kwargs)
        if pads.call_tracker.call_depth() == 1:
            network.add_edge(node_id, -1, plain_label=label, label=_step_number(network,label))
        elif pads.call_tracker.call_depth() > 1:
            containing_node_id = _to_node_id(pads.call_tracker.call_stack[-2].call_id.wrappee, ctx)
            if not network.has_node(containing_node_id):
                containing_node_label = _to_node_label(pads.call_tracker.call_stack[-2].call_id.wrappee, ctx)
                network.add_node(containing_node_id, label=containing_node_label)
            network.add_edge(node_id, containing_node_id, plain_label=label, label=_step_number(network,label))
        pipeline_cache["network"] = network
        pads.cache.add("pipeline", pipeline_cache)
