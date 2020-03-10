import threading
import time
from collections import OrderedDict

from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.logging_util import get_current_call_dict, get_function_id, get_instance_id

thread_local = threading.local()


def _init_local_index(call_id):
    global thread_local
    index = getattr(thread_local, 'index', None)
    if index is None:
        index = {}
        setattr(thread_local, 'index', index)
    if call_id not in index:
        index[call_id] = -1


def _get_local_index(call_id):
    global thread_local
    _init_local_index(call_id)
    return getattr(thread_local, 'index')[call_id]


def _increment_local_index(call_id):
    global thread_local
    _init_local_index(call_id)
    index_dict = getattr(thread_local, 'index')
    index_dict[call_id] += 1


def new_call_object(ctx, wrapped, self):
    from pypads.base import get_current_pads
    pads = get_current_pads()

    if not pads.cache.run_exists("call_objects"):
        pads.cache.run_add("call_objects", {})

    call_objects: dict = pads.cache.run_get("call_objects")

    function_id = get_function_id(ctx, wrapped)
    if function_id not in call_objects:
        call_objects[function_id] = OrderedDict()

    function_calls = call_objects[function_id]
    instance_id = get_instance_id(self)
    if instance_id not in function_calls:
        function_calls[instance_id] = []

    function_calls[instance_id].append({"started": time.time()})


class ObjectTracker(LoggingFunction):

    def __pre__(self, ctx, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
        new_call_object(_pypads_context, _pypads_wrappe, ctx)
        _increment_local_index(str(id(get_current_call_dict(ctx, _pypads_context, _pypads_wrappe))))
