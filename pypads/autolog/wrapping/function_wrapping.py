import types
from functools import wraps
from logging import warning, debug, info

from pypads.autolog.wrapping.base_wrapper import BaseWrapper, Context
from pypads.autolog.wrapping.module_wrapping import punched_module_names
from pypads.functions.analysis.call_tracker import CallAccessor, FunctionReference, add_call, LoggingEnv, finish_call, \
    Call


class FunctionWrapper(BaseWrapper):

    @classmethod
    def wrap(cls, fn, context: Context, mapping):
        # Only wrap functions not starting with "__"
        if not fn.__name__.startswith("__") or fn.__name__ is "__init__":
            context.store_wrap_meta(mapping, fn)
            if context.is_class():
                return cls._wrap_on_class(fn, context, mapping)
            elif hasattr(context.container, fn.__name__):
                return cls._wrap_on_object(fn, context, mapping)
            else:
                warning(str(
                    context) + " is no class and doesn't provide attribute with fn_name. Couldn't access " + str(
                    fn) + " on it.")
        else:
            return fn

    @classmethod
    def _wrap_on_object(cls, fn, context: Context, mapping):
        # Add module of class to the changed modules
        if hasattr(context.container, "__module__"):
            punched_module_names.add(context.container.__module__)

        # If we are already punched get original function instead of punched function
        if context.has_original(fn):
            fn = context.original(fn)
        else:
            fn = getattr(context.container, fn.__name__)

        # Get and add hooks
        hooks = cls._get_hooked_fns(fn, mapping)
        if len(hooks) > 0:
            fn_reference = FunctionReference(context, fn)
            return cls.wrap_method_helper(fn_reference=fn_reference, hooks=hooks, mapping=mapping)

    @classmethod
    def _wrap_on_class(cls, fn, context: Context, mapping):
        fn_name = fn.__name__

        # Find the real defining class
        defining_class = context.real_context(fn)

        # If there is no defining class we can't wrap on class
        if not defining_class:
            warning("Defining class is None. Omit logging.")
            return None

        # Add the module to the list of modules which where changed
        if hasattr(defining_class.container, "__module__"):
            punched_module_names.add(defining_class.container.__module__)

        # Get fn from defining class
        fn = None
        try:
            fn = getattr(defining_class.container, fn_name)
        except Exception as e:
            warning(str(e))

        # skip wrong extractions
        if not fn or not callable(fn):
            return fn

        # if we have a property we should use fget instead
        if isinstance(fn, property):
            fn = fn.fget

        # if ClassWrapper.has_original(fn_name, ctx):
        #     # TODO it would be nice if we could force super to return the here stated original function instead
        #     debug("Wrapping an already wrapped function: " + str(fn) + " on " + str(defining_class)
        #           + " with original: " +
        #           str(getattr(defining_class, ClassWrapper.original_name(fn_name, ctx)))
        #           + " The function may be wrapped on a superclass.")
        #     fn = getattr(defining_class, _to_original_name(fn_name, ctx))

        hooks = cls._get_hooked_fns(fn, mapping)
        if len(hooks) > 0:
            fn_reference = FunctionReference(defining_class, fn)
            return cls.wrap_method_helper(fn_reference=fn_reference, hooks=hooks, mapping=mapping)

    @classmethod
    def wrap_method_helper(cls, fn_reference: FunctionReference, hooks, mapping):
        """
        Helper to differentiate between functions, classmethods, static methods and wrap them
        :param fn_reference:
        :param hooks:
        :param mapping:
        :return:
        """
        fn = fn_reference.function

        if fn_reference.is_static_method():
            @wraps(fn)
            def entry(*args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                debug("Call to tracked static method or function " + str(fn))
                accessor = CallAccessor.from_function_reference(fn_reference, None)
                call = add_call(accessor)

                # add the function to the callback stack
                callback = accessor.function

                # for every hook add
                if cls._is_skip_recursion(accessor):
                    info("Skipping " + str(accessor.context.__name__) + "." + str(accessor.function.__name__))
                    out = callback(*args, **kwargs)
                    return out

                for (h, params, order) in hooks:
                    c = cls._add_hook(h, params, callback, call, mapping)
                    callback = c

                # start executing the stack
                out = callback(*args, **kwargs)
                finish_call(call)
                return out
        elif fn_reference.is_function():
            @wraps(fn)
            def entry(self, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                debug("Call to tracked method " + str(fn))
                accessor = CallAccessor.from_function_reference(fn_reference, None)
                call = add_call(accessor)

                # add the function to the callback stack
                callback = types.MethodType(accessor.function, self)

                # for every hook add
                if cls._is_skip_recursion(accessor):
                    info("Skipping " + str(accessor.context.__name__) + "." + str(accessor.function.__name__))
                    out = callback(*args, **kwargs)
                    return out

                for (h, params, order) in hooks:
                    c = cls._add_hook(h, params, callback, call, mapping)
                    callback = types.MethodType(c, self)

                # start executing the stack
                out = callback(*args, **kwargs)
                finish_call(call)
                return out

        elif fn_reference.is_class_method():
            @wraps(fn)
            def entry(cls, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                debug("Call to tracked class method " + str(fn))
                accessor = CallAccessor.from_function_reference(fn_reference, None)
                call = add_call(accessor)

                # add the function to the callback stack
                callback = types.MethodType(accessor.function, cls)

                # for every hook add
                if cls._is_skip_recursion(accessor):
                    info("Skipping " + str(accessor.context.__name__) + "." + str(accessor.function.__name__))
                    out = callback(*args, **kwargs)
                    return out

                for (h, params, order) in hooks:
                    c = cls._add_hook(h, params, callback, call, mapping)
                    callback = types.MethodType(c, cls)

                # start executing the stack
                out = callback(*args, **kwargs)
                finish_call(call)
                return out
        elif fn_reference.is_wrapped():
            tmp_fn = getattr(fn_reference.context, fn.__name__)

            @wraps(tmp_fn)
            def entry(self, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                debug("Call to tracked method " + str(fn))
                accessor = CallAccessor.from_function_reference(fn_reference, None)
                call = add_call(accessor)

                # add the function to the callback stack
                callback = types.MethodType(accessor.function, self)

                # for every hook add
                if cls._is_skip_recursion(accessor):
                    info("Skipping " + str(accessor.context.__name__) + "." + str(accessor.function.__name__))
                    out = callback(*args, **kwargs)
                    return out

                for (h, params, order) in hooks:
                    c = cls._add_hook(h, params, callback, call, mapping)
                    callback = types.MethodType(c, self)

                # start executing the stack
                out = callback(*args, **kwargs)
                finish_call(call)
                return out
        else:
            return fn
        fn_reference.context.overwrite(fn.__name__, entry)
        return entry

    @classmethod
    def _add_hook(cls, hook, params, callback, call: Call, mapping):
        # For every hook we defined on the given function in out mapping file execute it before running the code
        if not call.has_hook(hook):
            return cls._get_env_setter(_pypads_env=LoggingEnv(mapping, hook, params, callback, call))
        else:
            warning(str(hook) + " is tracked multiple times on " + str(call) + ". Ignoring second hooking.")

    @classmethod
    def _get_env_setter(cls, _pypads_env: LoggingEnv):
        """
        This wrapper sets the context
        :return:
        """
        env = _pypads_env
        call: Call = env.call
        cid = call.call_id

        if cid.is_static_method():
            @wraps(cid.function)
            def env_setter(*args, _pypads_env=env, **kwargs):
                debug("Static method hook " + str(cid.context) + str(cid.function) + str(env.hook))
                return cls._wrapped_inner_function(None, *args, _pypads_env=_pypads_env, **kwargs)

            return env_setter
        elif cid.is_function():
            @wraps(cid.function)
            def env_setter(self, *args, _pypads_env=env, **kwargs):
                debug("Method hook " + str(cid.context) + str(cid.function) + str(env.hook))
                return cls._wrapped_inner_function(self, *args, _pypads_env=_pypads_env, **kwargs)

            return env_setter
        elif cid.is_class_method():
            @wraps(cid.function)
            def env_setter(cls, *args, _pypads_env=env, **kwargs):
                debug("Class method hook " + str(cid.context) + str(cid.function) + str(env.hook))
                return cls._wrapped_inner_function(cls, *args, _pypads_env=_pypads_env,
                                                   **kwargs)

            return env_setter
        elif cid.is_wrapped():
            tmp_fn = getattr(cid.context, cid.function.__name__)

            @wraps(tmp_fn)
            def env_setter(self, *args, _pypads_env=env, **kwargs):
                debug("Method hook " + str(cid.context) + str(cid.function) + str(env.hook))
                return cls._wrapped_inner_function(self, *args, _pypads_env=_pypads_env, **kwargs)

            return env_setter
        else:
            raise ValueError("Failed!")

    @classmethod
    def _wrapped_inner_function(cls, _self, *args, _pypads_env: LoggingEnv, **kwargs):
        """
        Wrapped function logic. This executes all hooks and the function itself.
        :param _self:
        :param args:
        :param kwargs:
        :return:
        """

        env = _pypads_env
        call = env.call
        call.add_hook(env.hook)

        try:
            # check for name collision in parameters
            if set([k for k, v in kwargs.items()]) & set(
                    [k for k, v in env.parameter.items()]):
                warning("Hook parameter is overwriting a parameter in the standard "
                        "model call. This most likely will produce side effects.")

            if env.hook:
                return env.hook(_self, _pypads_env=_pypads_env, *args, **kwargs)
            return env.callback(*args, **kwargs)
        finally:
            call.remove_hook(env.hook)

    @classmethod
    def _is_skip_recursion(cls, accessor):
        from pypads.base import get_current_pads
        pads = get_current_pads()
        config = pads.config

        if 'recursion_depth' in config and config['recursion_depth'] is not -1:
            if pads.call_tracker.call_depth() > config['recursion_depth'] + 1:
                return True
        if 'recursion_identity' in config and config['recursion_identity']:
            if pads.call_tracker.has_call_identity(accessor):
                return True
        return False
