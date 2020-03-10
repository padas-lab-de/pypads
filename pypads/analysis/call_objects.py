import os
import threading
import time
from collections import OrderedDict

thread_local = threading.local()


def _init_local_index(call_id):
    index = getattr(thread_local, 'index', None)
    if index is None:
        index = {}
        setattr(thread_local, 'index', index)
    if call_id not in index:
        index[call_id] = -1


def _get_local_index(call_id):
    _init_local_index(call_id)
    return getattr(thread_local, 'index')[call_id]


def _increment_local_index(call_id):
    _init_local_index(call_id)
    index_dict = getattr(thread_local, 'index')
    index_dict[call_id] += 1


def get_function_id(ctx, wrapped):
    if hasattr(wrapped, "__name__"):
        if hasattr(ctx, wrapped.__name__):
            return id(getattr(ctx, wrapped.__name__))
    return str(id(ctx)) + "." + str(id(wrapped))


def get_instance_id(self):
    return id(self)


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


def get_current_call_dict(self, ctx, wrapped):
    from pypads.base import get_current_pads
    pads = get_current_pads()
    call_objects: dict = pads.cache.run_get("call_objects")
    function_calls: OrderedDict = call_objects[get_function_id(ctx, wrapped)]
    call_items = list(function_calls.items())
    instance_id = get_instance_id(self)

    instance_number = -1
    call_number = -1
    for instance_number in range(0, len(call_items)):
        # noinspection PyUnresolvedReferences
        key, value = call_items[instance_number]
        if key == instance_id:
            return value[-1]


def get_current_call_str(self, ctx, wrapped):
    from pypads.base import get_current_pads
    pads = get_current_pads()
    call_objects: dict = pads.cache.run_get("call_objects")
    function_calls: OrderedDict = call_objects[get_function_id(ctx, wrapped)]
    call_items = list(function_calls.items())
    instance_id = get_instance_id(self)

    instance_number = -1
    call_number = -1
    for instance_number in range(0, len(call_items)):
        # noinspection PyUnresolvedReferences
        key, value = call_items[instance_number]
        if key == instance_id:
            call_number = len(value)
            break

    return "thread_" + str(
        threading.get_ident()) + "." + "context_" + ctx.__name__ + ".instance_" + str(
        instance_number) + "." + "function_" + wrapped.__name__ + ".call_" + str(
        _get_local_index(str(id(get_current_call_dict(self, ctx, wrapped)))))


def get_current_call_folder(self, ctx, wrapped):
    from pypads.base import get_current_pads
    pads = get_current_pads()
    call_objects: dict = pads.cache.run_get("call_objects")
    function_calls: OrderedDict = call_objects[get_function_id(ctx, wrapped)]
    call_items = list(function_calls.items())
    instance_id = get_instance_id(self)

    instance_number = -1
    call_number = -1
    for instance_number in range(0, len(call_items)):
        # noinspection PyUnresolvedReferences
        key, value = call_items[instance_number]
        if key == instance_id:
            call_number = len(value)
            break

    return os.path.join("thread_" + str(threading.get_ident()), "context_" + ctx.__name__,
                        "instance_" + str(instance_number), "function_" + wrapped.__name__,
                        "call_" + str(_get_local_index(str(id(get_current_call_dict(self, ctx, wrapped))))))


def track_call_object(self, *args, _pypads_autologgers=None, _pypads_wrappe,
                      _pypads_context,
                      _pypads_mapped_by,
                      _pypads_callback, _pypads_hook_params, **kwargs):
    new_call_object(_pypads_context, _pypads_wrappe, self)
    _increment_local_index(str(id(get_current_call_dict(self, _pypads_context, _pypads_wrappe))))
    return _pypads_callback(*args, **kwargs)
