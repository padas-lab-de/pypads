import types
from contextlib import contextmanager
from functools import wraps

from pypads import logger
from pypads.autolog.wrapping.base_wrapper import BaseWrapper, Context
from pypads.autolog.wrapping.module_wrapping import punched_module_names
from pypads.functions.analysis.call_tracker import CallAccessor, FunctionReference, add_call, LoggingEnv, finish_call, \
    Call


class FunctionWrapper(BaseWrapper):

    @classmethod
    def wrap(cls, fn, context: Context, mapping):
        # Only wrap functions not starting with "__"
        if (fn.__name__.startswith("__") or fn.__name__.startswith("_pypads")) and fn.__name__ is not "__init__":
            return fn

        if not context.has_wrap_meta(mapping, fn):
            context.store_wrap_meta(mapping, fn)

            if not context.has_original(fn) or not context.defined_stored_original(fn):
                context.store_original(fn)

            if context.is_class():
                return cls._wrap_on_class(fn, context, mapping)
            elif hasattr(context.container, fn.__name__):
                return cls._wrap_on_object(fn, context, mapping)
            else:
                logger.warning(str(
                    context) + " is no class and doesn't provide attribute with fn_name. Couldn't access " + str(
                    fn) + " on it.")

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
        defining_class = context.real_context(fn.__name__)

        # If there is no defining class we can't wrap on class
        if not defining_class:
            logger.warning("Defining class is None on context '" + str(context) + "' for fn '" + str(
                fn) + "'. Class punching might be lost in newly spawned processes.")
        else:
            # Add the module to the list of modules which where changed
            if hasattr(defining_class.container, "__module__"):
                punched_module_names.add(defining_class.container.__module__)

            # Get real fn from defining class
            fn = None
            try:
                fn = getattr(defining_class.container, fn_name)
            except Exception as e:
                context.real_context(fn.__name__)
                logger.warning("Defining class doesn't define our function. Extraction failed: " + str(e))

        # skip wrong extractions
        if not fn or not callable(fn):
            return fn

        # if we have a property we should use fget instead
        if isinstance(fn, property):
            fn = fn.fget

        # if ClassWrapper.has_original(fn_name, ctx):
        #     # TODO it would be nice if we could force super to return the here stated original function instead
        #     logger.debug("Wrapping an already wrapped function: " + str(fn) + " on " + str(defining_class)
        #           + " with original: " +
        #           str(getattr(defining_class, ClassWrapper.original_name(fn_name, ctx)))
        #           + " The function may be wrapped on a superclass.")
        #     fn = getattr(defining_class, _to_original_name(fn_name, ctx))

        hooks = cls._get_hooked_fns(fn, mapping)
        if len(hooks) > 0:
            fn_reference = FunctionReference(context, fn)
            return cls.wrap_method_helper(fn_reference=fn_reference, hooks=hooks, mapping=mapping)

    @classmethod
    @contextmanager
    def _make_call(cls, instance, fn_reference):
        accessor = CallAccessor.from_function_reference(fn_reference, instance)

        current_call = None
        call = None
        try:
            from pypads.pypads import get_current_pads
            current_call: Call = get_current_pads().call_tracker.current_call()
            if current_call and accessor.is_call_identity(current_call.call_id):
                call = current_call
            else:
                call = add_call(accessor)
            yield call
        finally:
            if call and not current_call == call:
                # print("c:" + str(call))
                # print("cc:" + str(current_call))
                finish_call(call)

    @classmethod
    def wrap_method_helper(cls, fn_reference: FunctionReference, hooks, mapping):
        """
        Helper to differentiate between functions, classmethods, static methods and wrap them
        :param fn_reference:
        :param hooks:
        :param mapping:
        :return:
        """
        fn = fn_reference.wrappee

        if fn_reference.is_static_method():
            @wraps(fn)
            def entry(*args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                logger.debug("Call to tracked static method or function " + str(fn))

                with cls._make_call(None, fn_reference) as call:
                    accessor = call.call_id
                    callback = fn

                    # for every hook add
                    if cls._is_skip_recursion(accessor):
                        logger.info("Skipping " + str(accessor.context.container.__name__) + "." + str(
                            accessor.wrappee.__name__))
                        out = callback(*args, **kwargs)
                        return out

                    for (h, params) in hooks:
                        c = cls._add_hook(h, params, callback, call, mapping)
                        if c:
                            callback = c

                    # start executing the stack
                    out = callback(*args, **kwargs)
                return out
        elif fn_reference.is_function():
            @wraps(fn)
            def entry(self, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                # print("Call to tracked class method " + str(fn) + str(id(fn)))
                logger.debug("Call to tracked method " + str(fn))

                with cls._make_call(self, fn_reference) as call:
                    accessor = call.call_id
                    # add the function to the callback stack
                    callback = types.MethodType(fn, self)

                    # for every hook add
                    if cls._is_skip_recursion(accessor):
                        logger.info("Skipping " + str(accessor.context.container.__name__) + "." + str(
                            accessor.wrappee.__name__))
                        out = callback(*args, **kwargs)
                        return out

                    for (h, params) in hooks:
                        c = cls._add_hook(h, params, callback, call, mapping)
                        if c:
                            callback = types.MethodType(c, self)

                    # start executing the stack
                    out = callback(*args, **kwargs)
                return out

        elif fn_reference.is_class_method():
            @wraps(fn)
            def entry(cls, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                logger.debug("Call to tracked class method " + str(fn))
                with cls._make_call(cls, fn_reference) as call:
                    accessor = call.call_id
                    # add the function to the callback stack
                    callback = types.MethodType(fn, cls)

                    # for every hook add
                    if cls._is_skip_recursion(accessor):
                        logger.info("Skipping " + str(accessor.context.container.__name__) + "." + str(
                            accessor.wrappee.__name__))
                        out = callback(*args, **kwargs)
                        return out

                    for (h, params) in hooks:
                        c = cls._add_hook(h, params, callback, call, mapping)
                        if c:
                            callback = types.MethodType(c, cls)

                    # start executing the stack
                    out = callback(*args, **kwargs)
                return out

        elif fn_reference.is_wrapped():
            tmp_fn = getattr(fn_reference.context.container, fn.__name__)

            @wraps(tmp_fn)
            def entry(self, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                logger.debug("Call to tracked _IffHasAttrDescriptor " + str(fn))
                with cls._make_call(self, fn_reference) as call:
                    accessor = call.call_id
                    # add the function to the callback stack
                    callback = fn.__get__(self)

                    # for every hook add
                    if cls._is_skip_recursion(accessor):
                        logger.info("Skipping " + str(accessor.context.container.__name__) + "." + str(
                            accessor.wrappee.__name__))
                        out = callback(*args, **kwargs)
                        return out

                    for (h, params) in hooks:
                        c = cls._add_hook(h, params, callback, call, mapping)
                        if c:
                            callback = types.MethodType(c, self)

                    # start executing the stack
                    out = callback(*args, **kwargs)
                return out
        else:
            return fn
        fn_reference.context.overwrite(fn.__name__, entry)
        # print("Wrapped " + str(fn) + str(id(fn)))
        return entry

    @classmethod
    def _add_hook(cls, hook, params, callback, call: Call, mapping):
        # For every hook we defined on the given function in out mapping file execute it before running the code
        if not call.has_hook(hook):
            return cls._get_env_setter(_pypads_env=LoggingEnv(mapping, hook, params, callback, call))
        else:
            logger.debug(str(hook) + " is tracked multiple times on " + str(call) + ". Ignoring second hooking.")
            return None

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
            @wraps(cid.wrappee)
            def env_setter(*args, _pypads_env=env, **kwargs):
                logger.debug("Static method hook " + str(cid.context) + str(cid.wrappee) + str(env.hook))
                return cls._wrapped_inner_function(None, *args, _pypads_env=_pypads_env, **kwargs)

            return env_setter
        elif cid.is_function():
            @wraps(cid.wrappee)
            def env_setter(self, *args, _pypads_env=env, **kwargs):
                logger.debug("Method hook " + str(cid.context) + str(cid.wrappee) + str(env.hook))
                return cls._wrapped_inner_function(self, *args, _pypads_env=_pypads_env, **kwargs)

            return env_setter
        elif cid.is_class_method():
            @wraps(cid.wrappee)
            def env_setter(cls, *args, _pypads_env=env, **kwargs):
                logger.debug("Class method hook " + str(cid.context) + str(cid.wrappee) + str(env.hook))
                return cls._wrapped_inner_function(cls, *args, _pypads_env=_pypads_env,
                                                   **kwargs)

            return env_setter
        elif cid.is_wrapped():
            tmp_fn = getattr(cid.context.container, cid.wrappee.__name__)

            @wraps(tmp_fn)
            def env_setter(self, *args, _pypads_env=env, **kwargs):
                logger.debug("Method hook " + str(cid.context) + str(cid.wrappee) + str(env.hook))
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
                logger.warning("Hook parameter is overwriting a parameter in the standard "
                               "model call. This most likely will produce side effects.")

            if env.hook:
                return env.hook(_self, _pypads_env=_pypads_env, *args, **kwargs)
            return env.callback(*args, **kwargs)
        finally:
            call.remove_hook(env.hook)

    @classmethod
    def _is_skip_recursion(cls, accessor):
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        try:
            config = pads.config

            if 'recursion_depth' in config and config['recursion_depth'] is not -1:
                if pads.call_tracker.call_depth() > config['recursion_depth'] + 1:
                    return True
            if 'recursion_identity' in config and config['recursion_identity']:
                if pads.call_tracker.has_call_identity(accessor):
                    return True
            return False
        except Exception as e:
            return False
