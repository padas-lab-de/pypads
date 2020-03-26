from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.loggers.base_logger import LoggingFunction


class ParameterSearch(LoggingFunction):

    def __pre__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()
        pads.cache.add("parameter_search", ctx)

    def __post__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()

        pads.cache.pop("parameter_search")


class ParameterSearchExecutor(LoggingFunction):

    def __pre__(self, ctx, *args, **kwargs):
        pass

    def __post__(self, ctx, *args, **kwargs):
        pass

    def call_wrapped(self, ctx, *args, _pypads_env: LoggingEnv, _kwargs, **_pypads_hook_params):
        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()

        if pads.cache.exists("parameter_search"):
            with pads.api.intermediate_run():
                out = _pypads_env.callback(*args, **_kwargs)
            return out
        else:
            return _pypads_env.callback(*args, **_kwargs)
