import os

import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log
from pydantic import BaseModel
from pydantic.networks import HttpUrl
from typing import Type

from pypads import logger
from pypads.app.injections.base_logger import TrackedObject, LoggerCall
from pypads.app.injections.injection import InjectionLoggerCall, MultiInjectionLogger
from pypads.model.models import TrackedObjectModel, OutputModel, ArtifactMetaModel
from pypads.utils.logging_util import WriteFormats, get_temp_folder
from pypads.utils.util import is_package_available


# utilities
def _to_node_id(wrappee, ref):
    if ref is not None:
        return id(ref)
    else:
        return id(wrappee)


def _to_node_label(wrappee, ref):
    if ref is not None:
        try:
            return str(wrappee) + str(id(ref))
        except Exception as e:
            logger.warning("Couldn't get the representation of wrappee. Fallback to id " + str(id(ref)) + ". " + str(e))
            return str(id(wrappee)) + str(id(ref))
    else:
        try:
            return str(wrappee)
        except Exception as e:
            logger.warning(
                "Couldn't get representation of the wrappee. Fallback to id " + str(id(wrappee)) + ". " + str(e))
            return str(id(wrappee))


def _to_edge_label(wrappee, include_args, args, kwargs):
    if include_args:
        return str(wrappee) + " args: " + str(args) + " kwargs: " + str(kwargs)
    return str(wrappee)


def _step_number(network, label):
    return str(network.number_of_edges()) + ": " + label


class PipelineTO(TrackedObject):
    """
       Tracking object class for execution workflow/ computational graph.
    """

    class PipelineModel(TrackedObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/Pipeline"

        network: dict = ...
        pipeline_type: str = ...
        last_tracked: int = ...

        class Config:
            orm_mode = True
            arbitrary_types_allowed = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.PipelineModel

    def __init__(self, *args, tracked_by: LoggerCall, network=None, pipeline_type="", last_tracked=None, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, network=network, pipeline_type=pipeline_type,
                         last_tracked=last_tracked, **kwargs)

    def _get_network(self):
        return self.network

    def _set_network(self, network: dict):
        self.network = network

    def _get_last_tracked(self):
        return self.last_tracked

    def _set_last_tracked(self, last_tracked):
        self.last_tracked = last_tracked

    def _get_artifact_path(self, name=None):
        if name is not None:
            return os.path.join(str(id(self)), "pipeline", name)
        else:
            return os.path.join(str(id(self)), "pipeline",)


class PipelineTrackerILF(MultiInjectionLogger):
    """
    Injection logger that tracks multiple calls.
    """
    name = "PipeLineLogger"
    uri = "https://www.padre-lab.eu/onto/pipeline-logger"

    _dependencies = {"networkx"}

    class PipelineTrackerILFOutput(OutputModel):
        is_a: HttpUrl = "https://www.padre-lab.eu/onto/PipelineILF-Output"

        pipeline: PipelineTO.get_model_cls() = None

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls):
        return cls.PipelineTrackerILFOutput

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def store(pads, *args, **kwargs):
        pipeline_tracker = pads.cache.run_get(pads.cache.run_get("pipeline_tracker"))
        call = pipeline_tracker.get("call")
        output = pipeline_tracker.get("output")
        pipeline = output.pipeline

        from networkx import MultiDiGraph
        network = MultiDiGraph(pipeline._get_network())
        _pipeline_type = pipeline.pipeline_type
        # global network
        if network is not None and len(network.nodes) > 0:
            from networkx import DiGraph
            from networkx.drawing.nx_agraph import to_agraph
            path = os.path.join(pipeline._base_path(), pipeline._get_artifact_path("pypads_pipeline"))
            # try_write_artifact(path, network, WriteFormats.pickle)
            pipeline._store_artifact(network,
                                     ArtifactMetaModel(path=path, description="networkx graph",
                                                       format=WriteFormats.pickle))
            if is_package_available("networkx"):
                base_folder = get_temp_folder()
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
                    path = os.path.join(pipeline._base_path(), pipeline._get_artifact_path())
                    try_mlflow_log(mlflow.log_artifact, folder, artifact_path=path)

        call.output = output.store(pipeline_tracker.get("base_path"))
        call.store()

    def __pre__(self, ctx, *args, _logger_call: InjectionLoggerCall, _pypads_pipeline_type="normal",
                _pypads_pipeline_args=False, _logger_output,
                **kwargs):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        pads.cache.run_add("pipeline_tracker", id(self))

        if _logger_output.pipeline is None:
            pipeline = PipelineTO(tracked_by=_logger_call, pipeline_type=_pypads_pipeline_type)
        else:
            pipeline = _logger_output.pipeline

        network = pipeline.network
        last_tracked = pipeline.last_tracked
        _pipeline_type = pipeline.pipeline_type

        import networkx as nx
        if network is None:
            network = nx.MultiDiGraph()
        else:
            network = nx.MultiDiGraph(network)

        node_id = _to_node_id(_logger_call.original_call.call_id.wrappee, ctx)
        label = _to_node_label(_logger_call.original_call.call_id.wrappee, ctx)
        if not network.has_node(node_id):
            network.add_node(node_id, label=label)

        label = _to_edge_label(_logger_call.original_call.call_id.wrappee, _pypads_pipeline_args, args, kwargs)
        # If the current stack holds only the call itself
        if pads.call_tracker.call_depth() == 1:

            # If there where no nodes until now
            if len(network.nodes) == 1:
                network.add_node(-1, label="entry")
                last_tracked = -1
                pipeline._set_last_tracked(last_tracked)
            network.add_edge(last_tracked, node_id, plain_label=label, label=_step_number(network, label))

        # If the tracked function was called from another tracked function
        elif pads.call_tracker.call_depth() > 1:

            containing_node_id = _to_node_id(pads.call_tracker.call_stack[-2].call_id.wrappee, ctx)
            if not network.has_node(containing_node_id):
                containing_node_label = _to_node_label(pads.call_tracker.call_stack[-2].call_id.wrappee, ctx)
                network.add_node(containing_node_id, label=containing_node_label)
            # Add an edge from the tracked function to the current function call
            network.add_edge(containing_node_id, node_id, plain_label=label, label=_step_number(network, label))

        pipeline._set_network(nx.to_dict_of_dicts(network))
        pipeline.store(_logger_output, "pipeline")
        return node_id

    def __post__(self, ctx, *args, _pypads_pipeline_args=False, _logger_call: InjectionLoggerCall, _logger_output,
                 _pypads_pre_return,
                 **kwargs):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()

        import networkx as nx
        pipeline = _logger_output.pipeline
        network = nx.MultiDiGraph(pipeline._get_network())

        node_id = _pypads_pre_return
        label = "return " + _to_edge_label(_logger_call.original_call.call_id.wrappee, _pypads_pipeline_args, args,
                                           kwargs)
        if pads.call_tracker.call_depth() == 1:
            network.add_edge(node_id, -1, plain_label=label, label=_step_number(network, label))
        elif pads.call_tracker.call_depth() > 1:
            containing_node_id = _to_node_id(pads.call_tracker.call_stack[-2].call_id.wrappee, ctx)
            if not network.has_node(containing_node_id):
                containing_node_label = _to_node_label(pads.call_tracker.call_stack[-2].call_id.wrappee, ctx)
                network.add_node(containing_node_id, label=containing_node_label)
            network.add_edge(node_id, containing_node_id, plain_label=label, label=_step_number(network, label))
        pipeline._set_network(nx.to_dict_of_dicts(network))
        pipeline.store(_logger_output, "pipeline")
