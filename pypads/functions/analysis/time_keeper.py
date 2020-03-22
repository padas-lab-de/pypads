import time
from collections import OrderedDict
from logging import info

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
    from pypads.base import get_current_pads
    pads = get_current_pads()
    if not pads.cache.run_exists("logger_times"):
        pads.cache.run_add("logger_times", OrderedDict())
    logger_times: OrderedDict = pads.cache.run_get("logger_times")

    aggregated_times = []
    for k, v in logger_times.items():
        aggregated = 0
        for t in v:
            aggregated += t
        aggregated_times.append((k, aggregated))

    out = ""
    for k, v in sorted(aggregated_times, key=lambda x: -x[1]):
        out += k + " elapsed " + str(v) + "s.\n"
    return out


def print_timings():
    from pypads.base import get_current_pads
    pads = get_current_pads()

    timings: OrderedDict = pads.cache.run_get("timings")
    out = ""
    for k, v in timings.items():
        out += v + "\n"
    pads.api.log_mem_artifact("timings", out, write_format=WriteFormats.text.text)

    logger_time: OrderedDict = pads.cache.run_get("timings")
    out = ""
    for k, v in logger_time.items():
        out += k + " took " + v + ".\t"

    pads.api.log_mem_artifact("loggers", get_logger_times(), write_format=WriteFormats.text.text)


def add_run_time(logger, name, time):
    from pypads.base import get_current_pads
    pads = get_current_pads()

    pads.api.register_post_fn("timings", print_timings)

    if not pads.cache.run_exists("timings"):
        pads.cache.run_add("timings", OrderedDict())

    timings: OrderedDict = pads.cache.run_get("timings")
    if name not in timings:
        value = ""
        # dashes
        for i in range(1, pads.call_tracker.call_depth()):
            value += "\t"
        timings[name] = value + " " + name + ": " + str(time)
        info(name + " done after: " + str(time) + "s")
    else:
        raise TimingDefined("Timing already defined for " + name)

    # Add to logger time
    if logger:
        if not pads.cache.run_exists("logger_times"):
            pads.cache.run_add("logger_times", OrderedDict())
        logger_times: OrderedDict = pads.cache.run_get("logger_times")
        if logger.__class__.__name__ not in logger_times:
            logger_times[logger.__class__.__name__] = [time]
        else:
            logger_times[logger.__class__.__name__].append(time)
