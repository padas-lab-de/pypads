import ast
import inspect
import types
from logging import warning, debug, info

import mlflow
from boltons.funcutils import wraps

from pypads.autolog.hook import QualNameHook
from pypads.autolog.mapping import Mapping, found_classes, get_default_module_hooks, get_default_class_hooks, \
    get_default_fn_hooks
from pypads.logging_functions import log_init

punched_module = set()
punched_classes = set()

# stack of calls to a tracked class
current_tracking_stack = []


def wrap(wrappee, *args, **kwargs):
    """
    Wrap given object with pypads functionality
    :param wrappee:
    :param args:
    :param kwargs:
    :return:
    """
    if inspect.isclass(wrappee):
        wrap_class(wrappee, *args, **kwargs)

    elif inspect.isfunction(wrappee):
        wrap_function(wrappee.__name__, *args, **kwargs)


def wrap_module(module, mapping):
    """
    Function to wrap modules with pypads functionality
    :param module:
    :param mapping:
    :return:
    """
    if not hasattr(module, "_pypads_wrapped"):
        punched_module.add(module)
        if not mapping.hooks:
            mapping.hooks = get_default_module_hooks(mapping)

        for _name in dir(module):
            wrap(getattr(module, _name), module, mapping)

        for hook in mapping.hooks:
            if isinstance(hook, QualNameHook):
                found_classes[mapping.reference + "." + hook.name] = Mapping(mapping.reference + "." + hook.name,
                                                                             mapping.library, mapping.algorithm,
                                                                             mapping.file, mapping.hooks)

        setattr(module, "_pypads_wrapped", module)


def wrap_class(clazz, ctx, mapping):
    """
    Wrap a class in given ctx with pypads functionality
    :param clazz:
    :param ctx:
    :param mapping:
    :return:
    """
    if clazz not in punched_classes:
        if not mapping.hooks:
            mapping.hooks = get_default_class_hooks(mapping)

        if hasattr(clazz.__init__, "__module__"):
            original_init = getattr(clazz, "__init__")
            wrap_method_helper(fn=original_init, hooks=[(log_init, {})], mapping=mapping, ctx=clazz,
                               fn_type="function")

        if mapping.hooks:
            for hook in mapping.hooks:
                if isinstance(hook, QualNameHook):
                    wrap_function(hook.name, clazz, mapping)

        reference_name = mapping.reference.rsplit('.', 1)[-1]
        setattr(clazz, "_pypads_mapping", mapping)
        setattr(clazz, "_pypads_wrapped", clazz)
        setattr(ctx, reference_name, clazz)
        punched_classes.add(clazz)


def _get_hooked_fns(fn, mapping):
    """
    For a given fn find the hook functions defined in a mapping and configured in a configuration.
    :param fn:
    :param mapping:
    :return:
    """
    if not mapping.hooks:
        mapping.hooks = get_default_fn_hooks(mapping)

    # TODO filter for types, package name contains, etc. instead of only fn names
    hook_events_of_mapping = [hook.event for hook in mapping.hooks if hook.is_applicable(mapping=mapping, fn=fn)]
    output = []
    config = _get_pypads_config()
    for log_event, event_config in config["events"].items():
        configured_hook_events = event_config["on"]
        if "with" in event_config:
            hook_params = event_config["with"]
        else:
            hook_params = {}

        # If one configured_hook_events is in this config.
        if set(configured_hook_events) & set(hook_events_of_mapping):
            from pypads.base import get_current_pads
            pads = get_current_pads()
            fn = pads.function_registry.find_function(log_event)
            output.append((fn, hook_params))
    return output


def _wrapped_inner_function(ctx, *args, _pypads_hooked_fn, _pypads_hook_params, _pypads_wrappe, _pypads_context,
                            _pypads_callback, _pypads_mapped_by, **kwargs):
    """
    Wrapped function logic.
    :param ctx:
    :param args:
    :param _pypads_hooked_fn:
    :param _pypads_hook_params:
    :param _pypads_wrappe:
    :param _pypads_context:
    :param _pypads_item:
    :param _pypads_fn_stack:
    :param _pypads_mapped_by:
    :param kwargs:
    :return:
    """
    if ctx is not None:

        # Track hook execution to stop multiple exections of the same hook
        if not hasattr(ctx, "_pypads_active_calls"):
            setattr(ctx, "_pypads_active_calls", set())
        elif _pypads_hooked_fn in getattr(ctx, "_pypads_active_calls"):
            return _pypads_callback(*args, **kwargs)
        getattr(ctx, "_pypads_active_calls").add(_pypads_hooked_fn)

    try:

        # check for name collision
        if set([k for k, v in kwargs.items()]) & set(
                [k for k, v in _pypads_hook_params.items()]):
            warning("Hook parameter is overwriting a parameter in the standard "
                    "model call. This most likely will produce side effects.")

        if _pypads_hooked_fn:
            out = _pypads_hooked_fn(ctx, _pypads_wrappe=_pypads_wrappe, _pypads_context=_pypads_context,
                                    _pypads_callback=_pypads_callback,
                                    _pypads_mapped_by=_pypads_mapped_by,
                                    *args,
                                    **{**kwargs, **_pypads_hook_params})
        else:
            out = _pypads_callback(*args, **kwargs)
        if ctx is not None:
            getattr(ctx, "_pypads_active_calls").remove(_pypads_hooked_fn)
        return out
    except Exception as e:
        debug("Cleared cache entry for " + str(_pypads_wrappe) + " because of exception: " + str(e))
        if ctx is not None:
            getattr(ctx, "_pypads_active_calls").remove(_pypads_hooked_fn)
        raise e


def wrap_method_helper(fn, hooks, mapping, ctx, fn_type=None):
    """
    Helper to differentiate between functions, classmethods, static methods and wrap them
    :param fn:
    :param hook:
    :param params:
    :param stack:
    :param mapping:
    :param ctx:
    :param fn_type:
    :param last_element:
    :return:
    """

    def get_wrapper(_pypads_hooked_fn, _pypads_hook_params, _pypads_wrappe,
                    _pypads_context, _pypads_callback, _pypads_mapped_by):
        if not fn_type or "staticmethod" in str(fn_type):
            @wraps(fn)
            def ctx_setter(*args, _pypads_hooked_fn=_pypads_hooked_fn, _pypads_callback=_pypads_callback,
                           _pypads_hook_params=_pypads_hook_params, _pypads_mapped_by=_pypads_mapped_by, **kwargs):
                debug("Static method hook " + str(ctx) + str(fn) + str(_pypads_hooked_fn))
                return _wrapped_inner_function(None, *args, _pypads_hooked_fn=_pypads_hooked_fn,
                                               _pypads_hook_params=_pypads_hook_params, _pypads_wrappe=_pypads_wrappe,
                                               _pypads_context=_pypads_context,
                                               _pypads_callback=_pypads_callback, _pypads_mapped_by=_pypads_mapped_by,
                                               **kwargs)

            return ctx_setter
        elif "function" in str(fn_type):
            @wraps(fn)
            def ctx_setter(self, *args, _pypads_hooked_fn=_pypads_hooked_fn, _pypads_callback=_pypads_callback,
                           _pypads_hook_params=_pypads_hook_params, _pypads_mapped_by=_pypads_mapped_by, **kwargs):
                debug("Method hook " + str(ctx) + str(fn) + str(_pypads_hooked_fn))
                return _wrapped_inner_function(self, *args, _pypads_hooked_fn=_pypads_hooked_fn,
                                               _pypads_hook_params=_pypads_hook_params, _pypads_wrappe=_pypads_wrappe,
                                               _pypads_context=_pypads_context,
                                               _pypads_callback=_pypads_callback, _pypads_mapped_by=_pypads_mapped_by,
                                               **kwargs)

            return ctx_setter
        else:
            @wraps(fn)
            def ctx_setter(cls, *args, _pypads_hooked_fn=_pypads_hooked_fn, _pypads_callback=_pypads_callback,
                           _pypads_hook_params=_pypads_hook_params, _pypads_mapped_by=_pypads_mapped_by, **kwargs):
                debug("Class method hook " + str(ctx) + str(fn) + str(_pypads_hooked_fn))
                return _wrapped_inner_function(cls, *args, _pypads_hooked_fn=_pypads_hooked_fn,
                                               _pypads_hook_params=_pypads_hook_params, _pypads_wrappe=_pypads_wrappe,
                                               _pypads_context=_pypads_context,
                                               _pypads_callback=_pypads_callback, _pypads_mapped_by=_pypads_mapped_by,
                                               **kwargs)  #

            return ctx_setter

    setattr(ctx, "_pypads_mapping_" + fn.__name__, mapping)
    setattr(ctx, "_pypads_original_" + fn.__name__, fn)

    if not fn_type or "staticmethod" in str(fn_type):
        @wraps(fn)
        def entry(*args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
            debug("Call to tracked static method or function " + str(fn))
            current_tracking_stack.append((_pypads_mapped_by, ctx, fn, None))
            callback = fn
            if hooks:
                if _is_skip_recursion(None, _pypads_mapped_by):
                    info("Already tracked " + str(ctx.__name__) + "." + str(fn.__name__))
                    return callback(*args, **kwargs)

                for (hook, params) in hooks:
                    callback = get_wrapper(_pypads_hooked_fn=hook, _pypads_hook_params=params, _pypads_wrappe=fn,
                                           _pypads_context=ctx, _pypads_callback=callback, _pypads_mapped_by=mapping)
            out = callback(*args, **kwargs)
            current_tracking_stack.pop()
            return out
    elif "function" in str(fn_type):
        @wraps(fn)
        def entry(self, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
            debug("Call to tracked method " + str(fn))
            current_tracking_stack.append((_pypads_mapped_by, ctx, fn, self))
            callback = types.MethodType(fn, self)
            if hooks:
                if _is_skip_recursion(self, _pypads_mapped_by):
                    info("Already tracked " + str(ctx.__name__) + ": " + str(fn.__name__))
                    return callback(*args, **kwargs)

                for (hook, params) in hooks:
                    callback = types.MethodType(
                        get_wrapper(_pypads_hooked_fn=hook, _pypads_hook_params=params, _pypads_wrappe=fn,
                                    _pypads_context=ctx, _pypads_callback=callback, _pypads_mapped_by=mapping), self)

            out = callback(*args, **kwargs)
            current_tracking_stack.pop()
            return out

    elif "classmethod" in str(fn_type):
        @wraps(fn)
        def entry(cls, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, fn_type=fn_type, **kwargs):
            debug("Call to tracked class method " + str(fn))
            current_tracking_stack.append((_pypads_mapped_by, ctx, fn, cls))
            callback = types.MethodType(fn, cls)
            if hooks:
                if _is_skip_recursion(cls, _pypads_mapped_by):
                    info("Already tracked " + str(ctx.__name__) + ": " + str(fn.__name__))
                    return callback(*args, **kwargs)

                for (hook, params) in hooks:
                    callback = types.MethodType(
                        get_wrapper(_pypads_hooked_fn=hook, _pypads_hook_params=params, _pypads_wrappe=fn,
                                    _pypads_context=ctx, _pypads_callback=callback, _pypads_mapped_by=mapping), cls)
            out = callback(*args, **kwargs)
            current_tracking_stack.pop()
            return out
    else:
        return
    setattr(ctx, fn.__name__, entry)


def _is_skip_recursion(ref, mapping):
    config = _get_pypads_config()
    if 'recursion_depth' in config and config['recursion_depth'] is not -1:
        if len(current_tracking_stack) >= config['recursion_depth'] + 1:
            return True
        # found_entries = set()
        # for frame, filename, line_number, function_name, lines, index in inspect.stack():
        #     if "entry" in str(frame) and '_pypads_mapped_by' in frame.f_locals:
        #         mapped_by = frame.f_locals['_pypads_mapped_by']
        #         if len(found_entries) > config['recursion_depth']:
        #             return True
        #         else:
        #             found_entries.add(mapped_by)
    if 'recursion_identity' in config and config['recursion_identity']:
        for mapping, ctx, fn, cref in current_tracking_stack:
            if ref is not None and ref == cref:
                return True
        # found_entries = set()
        # for frame, filename, line_number, function_name, lines, index in inspect.stack():
        #     if "entry" in str(frame) and '_pypads_mapped_by' in frame.f_locals:
        #         mapped_by = frame.f_locals['_pypads_mapped_by']
        #         if mapped_by in found_entries:
        #             return True
        #         else:
        #             found_entries.add(mapped_by)
    return False


def wrap_function(fn_name, ctx, mapping):
    """
    Function to wrap the given fn_name on the ctx object with pypads function calls
    :param fn_name:
    :param ctx:
    :param mapping:
    :return:
    """
    if inspect.isclass(ctx):
        defining_class = None
        if not hasattr(ctx, "__dict__") or fn_name not in ctx.__dict__:
            mro = ctx.mro()
            for c in mro[1:]:
                defining_class = ctx
                if hasattr(ctx, "__dict__") and fn_name in defining_class.__dict__ and callable(
                        defining_class.__dict__[fn_name]):
                    break
                defining_class = None
        else:
            defining_class = ctx

        if defining_class:

            fn = None
            if hasattr(defining_class, "_pypads_original_" + fn_name):
                fn = getattr(defining_class, "_pypads_original_" + fn_name)
            else:
                try:
                    fn = getattr(defining_class, fn_name)
                except Exception as e:
                    warning(str(e))

            # skip wrong extractions TODO fix for structure like <class 'sklearn.utils.metaestimators._IffHasAttrDescriptor'>
            if not fn or not callable(fn):
                return

            if isinstance(fn, property):
                fn = fn.fget

            hooks = _get_hooked_fns(fn, mapping)
            if len(hooks) > 0:
                wrap_method_helper(fn=fn, hooks=hooks, mapping=mapping, ctx=ctx,
                                   fn_type=type(defining_class.__dict__[fn.__name__]))
    elif hasattr(ctx, fn_name):
        if hasattr(ctx, "_pypads_original_" + fn_name):
            fn = getattr(ctx, "_pypads_original_" + fn_name)
        else:
            fn = getattr(ctx, fn_name)
        hooks = _get_hooked_fns(fn, mapping)
        if len(hooks) > 0:
            wrap_method_helper(fn=fn, hooks=hooks, mapping=mapping, ctx=ctx)
    else:
        warning(ctx + " is no class or module. Couldn't access " + fn_name + " on it.")


# Cache configs for runs. Each run could is for now static in it's config.
configs = {}

# --- Clean cache after run ---
original_end = mlflow.end_run


def end_run(*args, **kwargs):
    configs.clear()
    return original_end(*args, **kwargs)


mlflow.end_run = end_run


# !--- Clean cache after run ---

def _get_pypads_config():
    """
    Get configuration defined in the current mlflow run
    :return:
    """
    global configs
    active_run = mlflow.active_run()
    if active_run in configs.keys():
        return configs[active_run]
    from pypads.base import get_current_pads
    from pypads.base import CONFIG_NAME
    pads = get_current_pads()
    run = pads.mlf.get_run(active_run.info.run_id)
    if CONFIG_NAME in run.data.tags:
        configs[active_run] = ast.literal_eval(run.data.tags[CONFIG_NAME])
        return configs[active_run]
    return {"events": {}, "recursive": True}
