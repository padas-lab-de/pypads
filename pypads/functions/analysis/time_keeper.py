import time
from collections import OrderedDict

from loguru import logger

from pypads.logging_util import WriteFormats


class TimingDefined(Exception):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def timed(f):
    start = time.time()
    ret = f()
    elapsed = time.time() - start
    return ret, elapsed


def get_logger_times():
    from pypads.pypads import get_current_pads
    pads = get_current_pads()

    timings: OrderedDict = pads.cache.run_get("timings")
    aggregated_times = {}
    for k, v in timings.items():
        splits = k.split(".")
        # Only loggers and not calls themselves
        if splits[-1] == "__pre__" or splits[-1] == "__post__":
            log_function = splits[-2]
            if log_function not in aggregated_times:
                aggregated_times[log_function] = 0
            aggregated_times[log_function] += float(v[1])

    out = ""
    for k, v in sorted(aggregated_times.items(), key=lambda x: -x[1]):
        out += k + " elapsed " + str(v) + "s.\n"
    return out


def print_timings():
    from pypads.pypads import get_current_pads
    pads = get_current_pads()

    timings: OrderedDict = pads.cache.run_get("timings")
    out = ""
    for k, v in timings.items():
        tabs = ""
        # depth
        for i in range(1, v[0]):
            tabs += "\t"
        out += tabs + str(k) + ": " + str(v[1]) + "\n"
    pads.api.log_mem_artifact("timings", out, write_format=WriteFormats.text.text)
    pads.api.log_mem_artifact("loggers", get_logger_times(), write_format=WriteFormats.text.text)


def add_run_time(log_function, name, time):
    from pypads.pypads import get_current_pads
    pads = get_current_pads()

    pads.api.register_post_fn("timings", print_timings)

    if not pads.cache.run_exists("timings"):
        pads.cache.run_add("timings", OrderedDict())

    timings: OrderedDict = pads.cache.run_get("timings")
    if name not in timings:
        timings[name] = (pads.call_tracker.call_depth(), time)
        logger.info(name + " done after: " + str(time) + "s")
    else:
        raise TimingDefined("Timing already defined for " + name)

    # # Add to logger time
    # if logger:
    #     if not pads.cache.run_exists("logger_times"):
    #         pads.cache.run_add("logger_times", OrderedDict())
    #     logger_times: OrderedDict = pads.cache.run_get("logger_times")
    #     if logger.__class__.__name__ not in logger_times:
    #         logger_times[logger.__class__.__name__] = [time]
    #     else:
    #         logger_times[logger.__class__.__name__].append(time)
