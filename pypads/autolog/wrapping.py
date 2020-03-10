import inspect
import types
from logging import warning, debug, info, error

from boltons.funcutils import wraps

from pypads.autolog.mappings import AlgorithmMapping

punched_module_names = set()
punched_classes = set()

# stack of calls to a tracked class
current_tracking_stack = []

DEFAULT_ORDER = 1


def _add_found_class(mapping):
    from pypads.base import get_current_pads
    get_current_pads().mapping_registry.add_found_class(mapping)


def wrap(wrappee, ctx, mapping):
    """
    Wrap given object with pypads functionality
    :param wrappee:
    :param args:
    :param kwargs:
    :return:
    """
    if inspect.isclass(wrappee):
        return wrap_class(wrappee, ctx, mapping)

    elif inspect.isfunction(wrappee):
        return wrap_function(wrappee, ctx, mapping)


def make_hook_applicable_filter(hook, ctx, mapping):
    """
    Create a filter to check if hook is applicable
    :param hook:
    :param ctx:
    :param mapping:
    :return:
    """

    def hook_applicable_filter(name):
        if hasattr(ctx, name):
            if not name.startswith("__") or name == "__init__":
                if not name.startswith("_pypads"):
                    try:
                        fn = getattr(ctx, name)
                        return hook.is_applicable(mapping=mapping, fn=fn)
                    except RecursionError as re:
                        error("Recursion error on '" + str(
                            ctx) + "'. This might be because __get_attr__ is being wrapped. " + str(re))
                else:
                    pass
                    # debug("Tried to wrap pypads function '" + name + "' on '" + str(ctx) + "'. Omit logging.")
            else:
                pass
                # debug(
                #     "Tried to wrap non-constructor native function '" + name + "' on '" + str(ctx) + "'. Omit logging.")
        else:
            warning("Can't access attribute '" + str(name) + "' on '" + str(ctx) + "'. Skipping.")
        return False

    return hook_applicable_filter


def wrap_module(module, mapping: AlgorithmMapping):
    """
    Function to wrap modules with pypads functionality
    :param module:
    :param mapping:
    :return:
    """
    if not hasattr(module, "_pypads_wrapped"):
        punched_module_names.add(module.__name__)
        if not mapping.hooks:
            mapping.hooks = mapping.in_collection.get_default_module_hooks()

        for _name in dir(module):
            wrap(getattr(module, _name), module, mapping)

        for hook in mapping.hooks:
            for name in list(filter(lambda x: make_hook_applicable_filter(hook, module, mapping), dir(module))):
                algorithm_mapping = AlgorithmMapping(mapping.reference + "." + name, mapping.library, mapping.algorithm,
                                                     mapping.file, None)
                algorithm_mapping.in_collection = mapping.in_collection
                _add_found_class(algorithm_mapping)

        try:
            setattr(module, "_pypads_wrapped", module)
        except TypeError as e:
            debug("Can't set attribute '_pypads_wrapped' on '" + str(module) + "'. Omit wrapping.")
            return module


def wrap_class(clazz, ctx, mapping):
    """
    Wrap a class in given ctx with pypads functionality
    :param clazz:
    :param ctx:
    :param mapping:
    :return:
    """
    if clazz not in punched_classes:
        if hasattr(clazz, "__module__"):
            punched_module_names.add(clazz.__module__)
        if not mapping.hooks:
            mapping.hooks = mapping.in_collection.get_default_class_hooks()

        try:
            setattr(clazz, "_pypads_mapping", mapping)
            setattr(clazz, "_pypads_wrapped", clazz)
        except TypeError as e:
            debug("Can't set attributes '_pypads_mapping', '_pypads_wrapped' on '" + str(clazz) + "'. Omit wrapping.")
            return clazz

        if mapping.hooks:
            for hook in mapping.hooks:
                for name in list(filter(make_hook_applicable_filter(hook, clazz, mapping), dir(clazz))):
                    wrap_function(name, clazz, mapping)

        reference_name = mapping.reference.rsplit('.', 1)[-1]
        punched_classes.add(clazz)
        if ctx is not None:
            setattr(ctx, reference_name, clazz)
    return clazz


def _get_hooked_fns(fn, mapping):
    """
    For a given fn find the hook functions defined in a mapping and configured in a configuration.
    :param fn:
    :param mapping:
    :return:
    """
    if not mapping.hooks:
        mapping.hooks = mapping.in_collection.get_default_fn_hooks()

    library = None
    version = None
    if mapping.in_collection is not None:
        library = mapping.in_collection.lib
        version = mapping.in_collection.lib_version
    hook_events_of_mapping = [hook.event for hook in mapping.hooks if hook.is_applicable(mapping=mapping, fn=fn)]
    output = []
    config = _get_current_config()
    for log_event, event_config in config["events"].items():
        configured_hook_events = event_config["on"]

        # Add by config defined parameters
        if "with" in event_config:
            hook_params = event_config["with"]
        else:
            hook_params = {}

        # Add an order
        if "order" in event_config:
            order = event_config["order"]
        else:
            order = DEFAULT_ORDER

        # If one configured_hook_events is in this config.
        if configured_hook_events == "always" or set(configured_hook_events) & set(hook_events_of_mapping):
            from pypads.base import get_current_pads
            pads = get_current_pads()
            fns = pads.function_registry.find_functions(log_event, lib=library, version=version)
            for fn in fns:
                output.append((fn, hook_params, order))
    output.sort(key=lambda t: t[2])
    return output


def _to_original_name(name, ctx):
    return "_pypads_original_" + str(id(ctx)) + "_" + name


def _get_original(name, ctx):
    try:
        return getattr(ctx, _to_original_name(name, ctx))
    except AttributeError:
        for attr in dir(ctx):
            if attr.endswith("_" + name) and attr.startswith("_pypads_original_"):
                return getattr(ctx, attr)


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
    if ctx is None:
        ctx = _pypads_context

    if ctx is not None:

        # Track hook execution to stop multiple exections of the same hook
        active_call = _pypads_hooked_fn

        # Track hook execution to stop multiple exections of the same hook
        if not hasattr(ctx, "_pypads_active_calls"):
            setattr(ctx, "_pypads_active_calls", set())
        elif active_call in getattr(ctx, "_pypads_active_calls"):
            return _pypads_callback(*args, **kwargs)
        getattr(ctx, "_pypads_active_calls").add(active_call)

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
                                    _pypads_hook_params=_pypads_hook_params,
                                    *args,
                                    **kwargs)
        else:
            out = _pypads_callback(*args, **kwargs)
        if ctx is not None:
            getattr(ctx, "_pypads_active_calls").remove(active_call)
        return out
    except Exception as e:

        # clear cache
        debug("Cleared cache entry for " + str(_pypads_wrappe) + " because of exception: " + str(e))
        if ctx is not None:
            if hasattr(ctx, "_pypads_active_calls"):
                getattr(ctx, "_pypads_active_calls").remove(active_call)

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

    # Get the wrapped function and set context
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
        elif "classmethod" in str(fn_type):
            @wraps(fn)
            def ctx_setter(cls, *args, _pypads_hooked_fn=_pypads_hooked_fn, _pypads_callback=_pypads_callback,
                           _pypads_hook_params=_pypads_hook_params, _pypads_mapped_by=_pypads_mapped_by, **kwargs):
                debug("Class method hook " + str(ctx) + str(fn) + str(_pypads_hooked_fn))
                return _wrapped_inner_function(cls, *args, _pypads_hooked_fn=_pypads_hooked_fn,
                                               _pypads_hook_params=_pypads_hook_params, _pypads_wrappe=_pypads_wrappe,
                                               _pypads_context=_pypads_context,
                                               _pypads_callback=_pypads_callback, _pypads_mapped_by=_pypads_mapped_by,
                                               **kwargs)

            return ctx_setter
        elif "sklearn_IffHasAttrDescriptor" == str(fn_type):
            tmp_fn = getattr(ctx, fn.__name__)

            @wraps(tmp_fn)
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
            raise ValueError("Failed!")

    try:
        setattr(ctx, "_pypads_mapping_" + fn.__name__, mapping)
        setattr(ctx, _to_original_name(fn.__name__, ctx), fn)
    except TypeError as e:
        debug("Can't set attribute '" + fn.__name__ + "' on '" + str(ctx) + "'. Omit wrapping.")
        return fn

    if not fn_type or "staticmethod" in str(fn_type):
        @wraps(fn)
        def entry(*args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
            debug("Call to tracked static method or function " + str(fn))
            current_tracking_stack.append((_pypads_mapped_by, ctx, fn, None))

            # add the function to the callback stack
            callback = fn

            # # track the execution time of the tracked function
            # callback = get_wrapper(_pypads_hooked_fn=time_keeper, _pypads_hook_params={"_pypads_time_kept": callback}, _pypads_wrappe=fn,
            #                                  _pypads_context=ctx, _pypads_callback=callback, _pypads_mapped_by=mapping)
            if hooks:
                if _is_skip_recursion(None, _pypads_mapped_by):
                    info("Skipping " + str(ctx.__name__) + "." + str(fn.__name__))
                    out = callback(*args, **kwargs)
                    current_tracking_stack.pop()
                    return out

                # For every hook we defined on the given function in out mapping file execute it before running the code
                for (hook, params, order) in hooks:
                    callback = get_wrapper(_pypads_hooked_fn=hook, _pypads_hook_params=params, _pypads_wrappe=fn,
                                           _pypads_context=ctx, _pypads_callback=callback,
                                           _pypads_mapped_by=mapping)
            # start executing the stack
            out = callback(*args, **kwargs)
            current_tracking_stack.pop()
            return out
    elif "function" in str(fn_type):
        @wraps(fn)
        def entry(self, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
            debug("Call to tracked method " + str(fn))
            current_tracking_stack.append((_pypads_mapped_by, ctx, fn, self))

            # add the function to the callback stack
            callback = types.MethodType(fn, self)

            # # track the execution time of the tracked function
            # callback = types.MethodType(get_wrapper(_pypads_hooked_fn=time_keeper, _pypads_hook_params={"_pypads_time_kept": callback}, _pypads_wrappe=fn,
            #                                  _pypads_context=ctx, _pypads_callback=callback, _pypads_mapped_by=mapping), self)
            if hooks:
                if _is_skip_recursion(self, _pypads_mapped_by):
                    info("Skipping " + str(ctx.__name__) + ": " + str(fn.__name__))
                    out = callback(*args, **kwargs)
                    current_tracking_stack.pop()
                    return out

                for (hook, params, order) in hooks:
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

            # add the function to the callback stack
            callback = types.MethodType(fn, cls)

            # # track the execution time of the tracked function
            # callback = types.MethodType(get_wrapper(_pypads_hooked_fn=time_keeper, _pypads_hook_params={"_pypads_time_kept": callback}, _pypads_wrappe=fn,
            #                                  _pypads_context=ctx, _pypads_callback=callback, _pypads_mapped_by=mapping), cls)
            if hooks:
                if _is_skip_recursion(cls, _pypads_mapped_by):
                    info("Skipping " + str(ctx.__name__) + ": " + str(fn.__name__))
                    out = callback(*args, **kwargs)
                    current_tracking_stack.pop()
                    return out

                for (hook, params, order) in hooks:
                    callback = types.MethodType(
                        get_wrapper(_pypads_hooked_fn=hook, _pypads_hook_params=params, _pypads_wrappe=fn,
                                    _pypads_context=ctx, _pypads_callback=callback, _pypads_mapped_by=mapping), cls)
            out = callback(*args, **kwargs)
            current_tracking_stack.pop()
            return out
    elif "sklearn_IffHasAttrDescriptor" == str(fn_type):
        tmp_fn = getattr(ctx, fn.__name__)

        @wraps(tmp_fn)
        def entry(self, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
            debug("Call to tracked method " + str(fn))
            current_tracking_stack.append((_pypads_mapped_by, ctx, fn, self))

            # add the function to the callback stack
            callback = fn.__get__(self)

            # # track the execution time of the tracked function
            # callback = types.MethodType(get_wrapper(_pypads_hooked_fn=time_keeper, _pypads_hook_params={"_pypads_time_kept": callback}, _pypads_wrappe=fn,
            #                                  _pypads_context=ctx, _pypads_callback=callback, _pypads_mapped_by=mapping), self)

            if hooks:
                if _is_skip_recursion(self, _pypads_mapped_by):
                    info("Skipping " + str(ctx.__name__) + ": " + str(fn.__name__))
                    out = callback(*args, **kwargs)
                    current_tracking_stack.pop()
                    return out

                for (hook, params, order) in hooks:
                    callback = types.MethodType(
                        get_wrapper(_pypads_hooked_fn=hook, _pypads_hook_params=params, _pypads_wrappe=fn,
                                    _pypads_context=ctx, _pypads_callback=callback, _pypads_mapped_by=mapping), self)

            out = callback(*args, **kwargs)
            current_tracking_stack.pop()
            return out
    else:
        return fn
    setattr(ctx, fn.__name__, entry)
    return entry


def _is_skip_recursion(ref, mapping):
    config = _get_current_config()
    if 'recursion_depth' in config and config['recursion_depth'] is not -1:
        if len(current_tracking_stack) > config['recursion_depth'] + 1:
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


def wrap_function(fn, ctx, mapping):
    """
    Function to wrap the given fn_name on the ctx object with pypads function calls
    :param fn:
    :param ctx:
    :param mapping:
    :return:
    """
    if callable(fn):
        fn_name = fn.__name__
    else:
        fn_name = fn
    if ctx is not None:
        if inspect.isclass(ctx):
            if hasattr(ctx, "__module__"):
                punched_module_names.add(ctx.__module__)
            defining_class = None
            if not hasattr(ctx, "__dict__") or fn_name not in ctx.__dict__:
                try:
                    mro = ctx.mro()
                    for c in mro[1:]:
                        defining_class = ctx
                        if hasattr(ctx, "__dict__") and fn_name in defining_class.__dict__ and callable(
                                defining_class.__dict__[fn_name]):
                            break
                        defining_class = None
                except Exception as e:
                    warning("Couldn't get defining class of context '" + str(ctx) + "'. Omit logging. " + str(e))
                    return fn
            else:
                defining_class = ctx

            if defining_class:
                if hasattr(defining_class, "__module__"):
                    punched_module_names.add(defining_class.__module__)

                fn = None
                try:
                    fn = getattr(defining_class, fn_name)
                except Exception as e:
                    warning(str(e))

                # skip wrong extractions
                if not fn or not callable(fn):
                    return fn

                if isinstance(fn, property):
                    fn = fn.fget

                if hasattr(defining_class, _to_original_name(fn_name, ctx)):
                    # TODO it would be nice if we could force super to return the here stated original function instead
                    debug("Wrapping an already wrapped function: " + str(fn) + " on " + str(
                        defining_class) + " with original: " +
                          str(getattr(defining_class, _to_original_name(fn_name,
                                                                        ctx))) + " The function may be wrapped on a superclass.")
                    fn = getattr(defining_class, _to_original_name(fn_name, ctx))

                hooks = _get_hooked_fns(fn, mapping)
                if len(hooks) > 0:
                    try:
                        function_type = type(defining_class.__dict__[fn.__name__])
                    except Exception as e:
                        warning("Couldn't get function type of '" + str(fn.__name__) + "' on '" + str(
                            defining_class) + ". Omit logging. " + str(e))
                        return fn
                    # TODO can we find less error prone ways to get the type of the given fn.
                    # Delegate decorator of sklearn obfuscates the real type.
                    if str(function_type) == "<class 'sklearn.utils.metaestimators._IffHasAttrDescriptor'>":
                        function_type = "sklearn_IffHasAttrDescriptor"
                        fn = defining_class.__dict__[fn.__name__]
                    return wrap_method_helper(fn=fn, hooks=hooks, mapping=mapping, ctx=ctx,
                                              fn_type=function_type)
        elif hasattr(ctx, fn_name):
            if hasattr(ctx, "__module__"):
                punched_module_names.add(ctx.__name__)
            if hasattr(ctx, _to_original_name(fn_name, ctx)):
                fn = getattr(ctx, _to_original_name(fn_name, ctx))
            else:
                fn = getattr(ctx, fn_name)
            hooks = _get_hooked_fns(fn, mapping)
            if len(hooks) > 0:
                return wrap_method_helper(fn=fn, hooks=hooks, mapping=mapping, ctx=ctx)
        else:
            warning(str(
                ctx) + " is no class and doesn't provide attribute with fn_name. Couldn't access " + fn_name + " on it.")
    else:
        class DummyClass:
            pass

        setattr(DummyClass, _to_original_name(fn.__name__, ctx), fn)

        # TODO what about punched_module_names

        hooks = _get_hooked_fns(fn, mapping)
        return wrap_method_helper(fn=fn, hooks=hooks, mapping=mapping, ctx=DummyClass)
    return fn


def _get_current_config():
    from pypads.base import get_current_config
    return get_current_config(default={"events": {}, "recursive": True})
