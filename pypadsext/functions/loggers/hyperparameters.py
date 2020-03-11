import sys

from pypads.functions.loggers.base_logger import LoggingFunction


class HyperParameters(LoggingFunction):

    def __pre__(self, ctx, *args, **kwargs):
        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()

        def tracer(frame, event, arg):
            if event == 'return':
                params = frame.f_locals.copy()
                key = kwargs['_pypads_callback'].__wrapped__.__qualname__ if hasattr(kwargs['_pypads_callback'],
                                                                                     "__wrapped__") else kwargs[
                    '_pypads_callback'].__qualname__
                pads.cache.run_add(key, params)

        # tracer is activated on next call, return or exception
        sys.setprofile(tracer)

    def call_wrapped(self, ctx, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                     _kwargs, **_pypads_hook_params):

        try:
            fn = _pypads_callback
            if hasattr(_pypads_callback, "__wrapped__"):
                fn = _pypads_callback.__wrapped__
            fn(*args, **_kwargs)
            self._fn = fn
        finally:
            # deactivate tracer
            sys.setprofile(None)

        return _pypads_callback(*args, **_kwargs)

    def __post__(self, ctx, *args, **kwargs):
        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()
        params = pads.cache.run_get(self._fn.__qualname__)
        for key, param in params.items():
            pads.api.log_param(key, param)
