import time
from collections import OrderedDict

from pypads.analysis.call_objects import get_current_call_str
from pypads.logging_util import WriteFormats


def timed(f):
    start = time.time()
    ret = f()
    elapsed = time.time() - start
    return ret, elapsed


def print_timings():
    from pypads.base import get_current_pads
    pads = get_current_pads()

    timings: OrderedDict = pads.cache.run_get("timings")
    out = ""
    for k, v in timings.items():
        out += v + "\n"
    pads.api.log_mem_artifact("timings", out, write_format=WriteFormats.text.text)


def add_run_time(name, time):
    from pypads.autolog.wrapping import current_tracking_stack
    from pypads.base import get_current_pads
    pads = get_current_pads()

    timings: OrderedDict = pads.cache.run_get("timings")

    value = ""
    # dashes
    for i in range(1, len(current_tracking_stack)):
        value += "\t"
    timings[name] = value + " " + name + ": " + str(time)


def time_keeper(self, *args, _pypads_wrappe,
                _pypads_context,
                _pypads_mapped_by,
                _pypads_time_kept,
                _pypads_callback, _pypads_hook_params, **kwargs):
    # TODO keep timings of post_fns running after a run
    from pypads.base import get_current_pads
    pads = get_current_pads()

    # We don't want to track the initial track_call_object
    if _pypads_time_kept.__name__ is 'track_call_object' and _pypads_callback is not _pypads_time_kept:
        return _pypads_time_kept(self, *args, _pypads_wrappe=_pypads_wrappe, _pypads_context=_pypads_context,
                                 _pypads_mapped_by=_pypads_mapped_by, _pypads_callback=_pypads_callback,
                                 _pypads_hook_params=_pypads_hook_params, **kwargs)

    pads.api.register_post_fn("timings", print_timings)

    if not pads.cache.run_exists("timings"):
        pads.cache.run_add("timings", OrderedDict())

    timings: OrderedDict = pads.cache.run_get("timings")

    if _pypads_callback is not _pypads_time_kept:
        name = "(" + get_current_call_str(self, _pypads_context,
                                          _pypads_wrappe) + ".pypads." + _pypads_time_kept.__name__ + ")"
        out, time = timed(
            lambda: _pypads_time_kept(self, *args, _pypads_wrappe=_pypads_wrappe, _pypads_context=_pypads_context,
                                      _pypads_mapped_by=_pypads_mapped_by, _pypads_callback=_pypads_callback,
                                      _pypads_hook_params=_pypads_hook_params, **kwargs))
        add_run_time(name, time)
    else:
        name = get_current_call_str(self, _pypads_context, _pypads_wrappe) + ":"
        out, time = timed(lambda: _pypads_time_kept(*args, **kwargs))
        add_run_time(name, time)

    return out


def time_kept(fn):
    def time_kept_function(self, *args, _pypads_wrappe,
                           _pypads_context,
                           _pypads_mapped_by,
                           _pypads_callback, _pypads_hook_params, **kwargs):
        return time_keeper(self, *args, _pypads_wrappe=_pypads_wrappe, _pypads_context=_pypads_context,
                           _pypads_mapped_by=_pypads_mapped_by, _pypads_time_kept=fn, _pypads_callback=_pypads_callback,
                           _pypads_hook_params=_pypads_hook_params,
                           **kwargs)

    return time_kept_function
