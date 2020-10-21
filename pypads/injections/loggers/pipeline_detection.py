import os
from dataclasses import dataclass
from typing import Type, Union

from pydantic import BaseModel

from pypads import logger
from pypads.app.env import LoggerEnv
from pypads.app.injections.injection import InjectionLoggerCall, MultiInjectionLogger, MultiInjectionLoggerCall
from pypads.app.injections.tracked_object import TrackedObject
from pypads.model.logger_call import InjectionLoggerCallModel
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.logging_util import get_temp_folder
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


@dataclass
class ProcessNode:
    process: int = ...

    def __str__(self):
        return "Process: " + str(self.process)

    def __hash__(self):
        return hash(self.process)


@dataclass
class ThreadNode:
    process_node: ProcessNode = ...
    thread: int = ...

    def __str__(self):
        return f"Thread: {str(self.thread)}, {self.process_node.__hash__()}"

    def __hash__(self):
        return hash((self.process_node.__hash__(), self.thread))


@dataclass
class ClassNode:
    thread_node: ThreadNode = ...
    clazz: str = ...

    def __str__(self):
        return f"Class: {str(self.clazz)}, {self.thread_node.__hash__()}"

    def __hash__(self):
        return hash((self.thread_node.__hash__(), self.clazz))


@dataclass
class InstanceNode:
    class_node: ClassNode = ...
    instance: int = ...

    def __str__(self):
        return f"Instance: {str(self.instance)}, {self.class_node.__hash__()}"

    def __hash__(self):
        return hash((self.class_node.__hash__(), self.instance))


@dataclass
class FunctionNode:
    instance_node: InstanceNode = ...
    function: str = ...

    def __str__(self):
        return f"Function: {str(self.function)}, {self.instance_node.__hash__()}"

    def __hash__(self):
        return hash((self.instance_node.__hash__(), self.function))


@dataclass
class CallNode:
    function_node: FunctionNode = ...
    call: int = ...

    def __str__(self):
        return f"Call: {str(self.call)}, {self.function_node.__hash__()}"

    def __hash__(self):
        return hash((self.function_node.__hash__(), self.call))


OF_EDGE = "part_of"
DATA_EDGE = "data_flow"
DATA_ID_EDGE = "data_id"
CALL_ORDER_EDGE = "call_order"


class PipelineTO(TrackedObject):
    """
       Tracking object class for execution workflow/ computational graph.
    """

    class PipelineModel(TrackedObjectModel):
        type: str = "Pipeline"
        description = "The Pipeline of the experiment."

        network: dict = ...
        pipeline_type: str = ...
        number_of_steps: int = ...

        class Config:
            orm_mode = True
            arbitrary_types_allowed = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.PipelineModel

    def __init__(self, *args, network=None, pipeline_type="", **kwargs):
        self._data_flow = {}
        self._data_id_flow = {}
        self._last_tracked = None
        self._number_of_steps = 0
        self._network = network
        super().__init__(*args, pipeline_type=pipeline_type, **kwargs)

    def _get_network(self):
        return self.network

    def _set_network(self, network: dict):
        self.network = network

    @property
    def network(self):
        import networkx as nx
        return self._convert_nodes_to_str(nx.to_dict_of_dicts(self._network))

    def _convert_nodes_to_str(self, network_dict):
        out = {}
        for k, v in network_dict.items():
            if isinstance(v, dict):
                out[self._convert_node_to_str(k)] = self._convert_nodes_to_str(v)
            else:
                out[self._convert_node_to_str(k)] = v
        return out

    @staticmethod
    def _convert_node_to_str(node):
        if isinstance(node, str):
            return node
        else:
            return str(node)

    @property
    def nx_network(self):
        return self._network

    @network.setter
    def network(self, value):
        self._network = value

    @property
    def last_tracked(self):
        return self._last_tracked

    @last_tracked.setter
    def last_tracked(self, value):
        self._last_tracked = value

    @property
    def number_of_steps(self):
        return self._number_of_steps

    def increment_step(self):
        self._number_of_steps += 1
        return self._number_of_steps

    @property
    def data_flow(self):
        return self._data_flow

    def add_data_hash(self, hash, node):
        self._data_flow[hash] = node

    @property
    def data_id_flow(self):
        return self._data_id_flow

    def add_data_id(self, uid, node):
        self._data_id_flow[uid] = node


class PipelineTrackerILF(MultiInjectionLogger):
    """
    Injection logger to track the execution graph of calls themselves. The logger itself uses networkx to build a
    call graph.
    """
    name = "Generic Pipeline Logger"
    type: str = "PipelineLogger"

    _dependencies = {"networkx"}

    class PipelineTrackerILFOutput(OutputModel):
        type: str = "PipelineILF-Output"
        pipeline_ref: str = None

        class Config:
            orm_mode = True

    @property
    def pipeline(self):
        return self._pipeline

    @pipeline.setter
    def pipeline(self, value):
        self._pipeline = value

    @classmethod
    def output_schema_class(cls):
        return cls.PipelineTrackerILFOutput

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pipeline = None

    @staticmethod
    def finalize_output(pads, logger_call, output, *args, **kwargs):
        pipeline: PipelineTO = pads.cache.run_get("pipeline")

        from networkx import MultiDiGraph
        network: MultiDiGraph = pipeline.nx_network

        base_folder = get_temp_folder()
        path = os.path.join(base_folder, "pipeline_graph.png")
        if not os.path.exists(base_folder):
            os.mkdir(base_folder)

        if is_package_available("agraph") and is_package_available("graphviz") and is_package_available("pygraphviz"):
            from networkx.drawing.nx_agraph import to_agraph
            agraph = to_agraph(network)
            agraph.layout('dot')
            agraph.draw(path)
            pipeline.store_artifact(path, "pipeline_graph.png",
                                    description="A depiction of the underlying pipeline of the experiment.")

        output.pipeline = pipeline.store()

        # # global network
        # if network is not None and len(network.nodes) > 0:
        #     from networkx import DiGraph
        #     from networkx.drawing.nx_agraph import to_agraph
        #     path = "pypads_pipeline"
        #     pipeline.store_artifact(network,
        #                             ArtifactMetaModel(path=path, description="networkx graph",
        #                                               format=FileFormats.pickle))
        #     if is_package_available("networkx"):
        #         base_folder = get_temp_folder()
        #         folder = base_folder + "pipeline_graph.png"
        #         if not os.path.exists(base_folder):
        #             os.mkdir(base_folder)
        #         if is_package_available("agraph") and is_package_available("graphviz"):
        #             try:
        #                 if _pipeline_type == "simple":
        #                     agraph = to_agraph(DiGraph(network))
        #                 elif _pipeline_type == "grouped":
        #                     copy = network.copy()
        #                     edge_groups = {}
        #                     for edge in copy.edges:
        #                         plain = copy.get_edge_data(*edge)['plain_label']
        #                         if plain not in edge_groups:
        #                             edge_groups[plain] = []
        #                         edge_groups[plain].append(edge)
        #
        #                     for group, edges in edge_groups.items():
        #                         label = ""
        #                         suffix = ""
        #                         base_edge = None
        #                         for edge in edges:
        #                             splits = copy.get_edge_data(*edge)['label'].split(":")
        #                             if label == "":
        #                                 label = splits[0]
        #                                 suffix = splits[1]
        #                                 base_edge = edge
        #                             else:
        #                                 label = label + ", " + splits[0]
        #                             copy.remove_edge(*edge)
        #                         label = label + ":" + suffix
        #                         copy.add_edge(*base_edge, label=label)
        #                     agraph = to_agraph(copy)
        #                 elif _pipeline_type == "grouped_no_count":
        #                     copy = network.copy()
        #                     edge_groups = {}
        #                     for edge in copy.edges:
        #                         plain = copy.get_edge_data(*edge)['plain_label']
        #                         if plain not in edge_groups:
        #                             edge_groups[plain] = edge
        #
        #                     copy.remove_edges_from(network.edges())
        #                     for group, edge in edge_groups.items():
        #                         copy.add_edge(*edge, label=group)
        #                     agraph = to_agraph(copy)
        #                 else:
        #                     agraph = to_agraph(network)
        #                 agraph.layout('dot')
        #                 agraph.draw(folder)
        #             except ValueError as e:
        #                 logger.warning("Failed plotting pipeline: " + str(e))
        #         elif is_package_available("matplotlib"):
        #             import matplotlib.pyplot as plt
        #             import networkx as nx
        #             pos = nx.spring_layout(network)
        #             nx.draw(network, pos)
        #             nx.draw_networkx_labels(network, pos=pos)
        #             nx.draw_networkx_edge_labels(network, pos)
        #             plt.savefig(folder)
        #         if os.path.exists(folder):
        #             path = "pipeline"
        #             try_mlflow_log(mlflow.log_artifact, folder, artifact_path=path)
        #
        # pipeline.store()
        # call.output = output.store()
        # call.store()

    @staticmethod
    def _add_to_network(node, network):
        if not network.has_node(node):
            network.add_node(node, label=str(node))

    @staticmethod
    def _add_of_edge(child, parent, network):
        if not network.has_edge(child, parent, OF_EDGE):
            network.add_edge(child, parent, plain_label=OF_EDGE, label=OF_EDGE)

    def __pre__(self, ctx, *args, _logger_call: Union[MultiInjectionLoggerCall, InjectionLoggerCallModel],
                _pypads_pipeline_type="normal", _pypads_pipeline_args=False, _pypads_env: LoggerEnv, _logger_output,
                **kwargs):
        """
        Add entry to the pipeline network.
        """

        # Initialized the pipeline_tracker by adding itself to the cache
        pads = _pypads_env.pypads

        # Get the network from the shared logger output
        import networkx as nx
        if not pads.cache.run_exists("pipeline"):
            pipeline = PipelineTO(network=nx.MultiDiGraph(), parent=_logger_output, pipeline_type=_pypads_pipeline_type)
            pads.cache.run_add("pipeline", pipeline)
        else:
            pipeline = pads.cache.run_get("pipeline")

        network = pipeline.nx_network

        # Convert current call to a nodes
        # TODO original call references the first call of the multi_injection_logger
        process_node = ProcessNode(process=_logger_call.call_stack[-1].call_id.process)
        thread_node = ThreadNode(thread=_logger_call.call_stack[-1].call_id.thread, process_node=process_node)
        class_node = ClassNode(clazz=ctx.__class__.__name__, thread_node=thread_node)
        instance_node = InstanceNode(instance=_logger_call.call_stack[-1].call_id.instance_id, class_node=class_node)
        function_node = FunctionNode(function=_logger_call.call_stack[-1].call_id.fn_name, instance_node=instance_node)
        call_node = CallNode(call=_logger_call.call_stack[-1].call_id.call_number, function_node=function_node)

        # Add nodes to network
        self._add_to_network(process_node, network)
        self._add_to_network(thread_node, network)
        self._add_to_network(class_node, network)
        self._add_to_network(instance_node, network)
        self._add_to_network(function_node, network)
        self._add_to_network(call_node, network)

        # Interlink nodes via of_edges
        self._add_of_edge(thread_node, process_node, network)
        self._add_of_edge(class_node, thread_node, network)
        self._add_of_edge(instance_node, class_node, network)
        self._add_of_edge(function_node, instance_node, network)
        self._add_of_edge(call_node, function_node, network)

        # Add entry edge if needed
        if len(network.nodes) == 6:
            network.add_node(-1, label="entry")
            network.add_edge(-1, call_node, plain_label=CALL_ORDER_EDGE,
                             label=f"{pipeline.number_of_steps}:{CALL_ORDER_EDGE}")

        # Add order edge
        if pipeline.last_tracked is not None:
            network.add_edge(pipeline.last_tracked, call_node, plain_label=CALL_ORDER_EDGE,
                             label=f"{pipeline.increment_step()}:{CALL_ORDER_EDGE}")

        # Add data edges
        for val in kwargs["_args"]:
            self._check_data_edge(val, call_node, pipeline)

        # Add data edges
        for _, val in kwargs["_kwargs"].items():
            self._check_data_edge(val, call_node, pipeline)

        pipeline.last_tracked = call_node
        return call_node

    @staticmethod
    def _check_data_edge(val, call_node, pipeline):
        """
        Add data flow edges depending on the hash of the data and the id of the data
        """
        network = pipeline.nx_network
        if id(val) in pipeline.data_flow:
            network.add_edge(pipeline.data_flow[id(val)], call_node, plain_label=DATA_ID_EDGE,
                             label=DATA_ID_EDGE)
            # try:
            #     data_hash = persistent_hash(val)
            #     if data_hash in pipeline.data_flow:
            #         network.add_edge(pipeline.data_flow[data_hash], call_node, plain_label=DATA_EDGE,
            #                          label=DATA_EDGE)
            # except Exception:
            #     pass

    def __post__(self, ctx, *args, _pypads_pipeline_args=False, _logger_call: InjectionLoggerCall, _logger_output,
                 _pypads_pre_return, _pypads_result, _pypads_env, **kwargs):
        pads = _pypads_env.pypads
        pipeline = pads.cache.run_get("pipeline")
        # try:
        #     pipeline.add_data_hash(persistent_hash(_pypads_result), _pypads_pre_return)
        # except Exception:
        #     pass
        if isinstance(_pypads_result, tuple):
            for val in _pypads_result:
                pipeline.add_data_id(id(val), _pypads_pre_return)
        pipeline.add_data_id(id(_pypads_result), _pypads_pre_return)
