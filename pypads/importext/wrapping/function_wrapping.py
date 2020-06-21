import types
from contextlib import contextmanager
from functools import wraps

from pypads import logger
from pypads.importext.wrapping.base_wrapper import BaseWrapper, Context
from pypads.injections.analysis.call_tracker import CallAccessor, FunctionReference, add_call, LoggingEnv, finish_call, \
    Call

error = False


class FunctionWrapper(BaseWrapper):

    def wrap(self, fn, context: Context, matched_mapping):
        # Only wrap functions not starting with "__"
        if (fn.__name__.startswith("__") or fn.__name__.startswith("_pypads")) and fn.__name__ is not "__init__":
            return fn

        if not context.has_wrap_meta(matched_mapping.mapping, fn):
            context.store_wrap_meta(matched_mapping, fn)

            if not context.has_original(fn) or not context.defined_stored_original(fn):
                context.store_original(fn)

            if context.is_class():
                return self._wrap_on_class(fn, context, matched_mapping.mapping)
            elif hasattr(context.container, fn.__name__):
                return self._wrap_on_object(fn, context, matched_mapping.mapping)
            else:
                logger.warning(str(
                    context) + " is no class and doesn't provide attribute with name " + str(
                    fn.__name__) + ". Couldn't access " + str(
                    fn) + " on it.")

    def _wrap_on_object(self, fn, context: Context, mapping):
        # Add module of class to the changed modules
        if hasattr(context.container, "__module__"):
            self._pypads.add_punched_module_name(context.container.__module__)

        # If we are already punched get original function instead of punched function
        if context.has_original(fn):
            fn = context.original(fn)
        else:
            fn = getattr(context.container, fn.__name__)

        # Get and add hooks
        hooks = self._get_hooked_fns(mapping)
        if len(hooks) > 0:
            fn_reference = FunctionReference(context, fn)
            return self.wrap_method_helper(fn_reference=fn_reference, hooks=hooks, mapping=mapping)
        else:
            return fn

    def _wrap_on_class(self, fn, context: Context, mapping):
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
                self._pypads.wrap_manager.module_wrapper.add_punched_module_name(defining_class.container.__module__)

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

        hooks = self._get_hooked_fns(mapping)
        if len(hooks) > 0:
            fn_reference = FunctionReference(context, fn)
            return self.wrap_method_helper(fn_reference=fn_reference, hooks=hooks, mapping=mapping)

    @contextmanager
    def _make_call(self, instance, fn_reference):
        accessor = CallAccessor.from_function_reference(fn_reference, instance)

        current_call = None
        call = None
        try:
            current_call: Call = self._pypads.call_tracker.current_call()
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

    def wrap_method_helper(self, fn_reference: FunctionReference, hooks, mapping):
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

                global error
                if self._pypads.api.active_run():
                    error = False
                    with self._make_call(None, fn_reference) as call:
                        accessor = call.call_id
                        callback = fn

                        # for every hook add
                        if self._is_skip_recursion(accessor):
                            logger.info("Skipping " + str(accessor.context.container.__name__) + "." + str(
                                accessor.wrappee.__name__))
                            out = callback(*args, **kwargs)
                            return out

                        for (h, params) in hooks:
                            c = self._add_hook(h, params, callback, call, mapping)
                            if c:
                                callback = c

                        # start executing the stack
                        out = callback(*args, **kwargs)
                else:
                    if not error:
                        error = True
                        logger.error(
                            "No run was active to log your hooks. You may want to start a run with PyPads().start_track()")
                    out = fn(*args, **kwargs)
                return out
        elif fn_reference.is_function():
            @wraps(fn)
            def entry(_self, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                # print("Call to tracked class method " + str(fn) + str(id(fn)))
                logger.debug("Call to tracked method " + str(fn))

                global error
                if self._pypads.api.active_run():
                    error = False
                    with self._make_call(_self, fn_reference) as call:
                        accessor = call.call_id
                        # add the function to the callback stack
                        callback = types.MethodType(fn, _self)

                        # for every hook add
                        if self._is_skip_recursion(accessor):
                            logger.info("Skipping " + str(accessor.context.container.__name__) + "." + str(
                                accessor.wrappee.__name__))
                            out = callback(*args, **kwargs)
                            return out

                        for (h, params) in hooks:
                            c = self._add_hook(h, params, callback, call, mapping)
                            if c:
                                callback = types.MethodType(c, _self)

                        # start executing the stack
                        out = callback(*args, **kwargs)
                else:
                    if not error:
                        error = True
                        logger.error(
                            "No run was active to log your hooks. You may want to start a run with PyPads().start_track()")
                    callback = types.MethodType(fn, _self)
                    out = callback(*args, **kwargs)
                return out

        elif fn_reference.is_class_method():
            @wraps(fn)
            def entry(_cls, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                logger.debug("Call to tracked class method " + str(fn))

                global error
                if self._pypads.api.active_run():
                    error = False
                    with self._make_call(_cls, fn_reference) as call:
                        accessor = call.call_id
                        # add the function to the callback stack
                        callback = types.MethodType(fn, _cls)

                        # for every hook add
                        if self._is_skip_recursion(accessor):
                            logger.info("Skipping " + str(accessor.context.container.__name__) + "." + str(
                                accessor.wrappee.__name__))
                            out = callback(*args, **kwargs)
                            return out

                        for (h, params) in hooks:
                            c = self._add_hook(h, params, callback, call, mapping)
                            if c:
                                callback = types.MethodType(c, _cls)

                        # start executing the stack
                        out = callback(*args, **kwargs)
                else:
                    if not error:
                        error = True
                        logger.error(
                            "No run was active to log your hooks. You may want to start a run with PyPads().start_track()")
                    callback = types.MethodType(fn, _cls)
                    out = callback(*args, **kwargs)
                return out

        elif fn_reference.is_wrapped():
            tmp_fn = getattr(fn_reference.context.container, fn.__name__)

            @wraps(tmp_fn)
            def entry(_self, *args, _pypads_hooks=hooks, _pypads_mapped_by=mapping, **kwargs):
                logger.debug("Call to tracked _IffHasAttrDescriptor " + str(fn))

                global error
                if self._pypads.api.active_run():
                    error = False
                    with self._make_call(_self, fn_reference) as call:
                        accessor = call.call_id
                        # add the function to the callback stack
                        callback = fn.__get__(_self)

                        # for every hook add
                        if self._is_skip_recursion(accessor):
                            logger.info("Skipping " + str(accessor.context.container.__name__) + "." + str(
                                accessor.wrappee.__name__))
                            out = callback(*args, **kwargs)
                            return out

                        for (h, params) in hooks:
                            c = self._add_hook(h, params, callback, call, mapping)
                            if c:
                                callback = types.MethodType(c, _self)

                        # start executing the stack
                        out = callback(*args, **kwargs)
                else:
                    if not error:
                        error = True
                        logger.error(
                            "No run was active to log your hooks. You may want to start a run with PyPads().start_track()")

                    callback = fn.__get__(_self)
                    out = callback(*args, **kwargs)
                return out
        else:
            return fn
        fn_reference.context.overwrite(fn.__name__, entry)
        # print("Wrapped " + str(fn) + str(id(fn)))
        return entry

    def _add_hook(self, hook, params, callback, call: Call, mapping):
        # For every hook we defined on the given function in out mapping file execute it before running the code
        if not call.has_hook(hook):
            return self._get_env_setter(_pypads_env=LoggingEnv(mapping, hook, params, callback, call))
        else:
            logger.debug(str(hook) + " is tracked multiple times on " + str(call) + ". Ignoring second hooking.")
            return None

    def _get_env_setter(self, _pypads_env: LoggingEnv):
        """
        This wrapper sets the context
        :return:
        """
        env = _pypads_env
        call: Call = env.call
        cid = call.call_id

        # TODO maybe use https://gist.github.com/MacHu-GWU/0170849f693aa5f8d129aa03fc358305
        if cid.is_static_method():
            @wraps(cid.wrappee)
            def env_setter(*args, _pypads_env=env, **kwargs):
                logger.debug("Static method hook " + str(cid.context) + str(cid.wrappee) + str(env.hook))
                return self._wrapped_inner_function(None, *args, _pypads_env=_pypads_env, **kwargs)

            return env_setter
        elif cid.is_function():
            @wraps(cid.wrappee)
            def env_setter(_self, *args, _pypads_env=env, **kwargs):
                logger.debug("Method hook " + str(cid.context) + str(cid.wrappee) + str(env.hook))
                return self._wrapped_inner_function(_self, *args, _pypads_env=_pypads_env, **kwargs)

            return env_setter
        elif cid.is_class_method():
            @wraps(cid.wrappee)
            def env_setter(_cls, *args, _pypads_env=env, **kwargs):
                logger.debug("Class method hook " + str(cid.context) + str(cid.wrappee) + str(env.hook))
                return self._wrapped_inner_function(_cls, *args, _pypads_env=_pypads_env,
                                                    **kwargs)

            return env_setter
        elif cid.is_wrapped():
            tmp_fn = getattr(cid.context.container, cid.wrappee.__name__)

            @wraps(tmp_fn)
            def env_setter(_self, *args, _pypads_env=env, **kwargs):
                logger.debug("Method hook " + str(cid.context) + str(cid.wrappee) + str(env.hook))
                return self._wrapped_inner_function(_self, *args, _pypads_env=_pypads_env, **kwargs)

            return env_setter
        else:
            raise ValueError("Failed!")

    def _wrapped_inner_function(self, _self, *args, _pypads_env: LoggingEnv, **kwargs):
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

    def _is_skip_recursion(self, accessor):
        try:
            config = self._pypads.config

            if 'recursion_depth' in config and config['recursion_depth'] is not -1:
                if self._pypads.call_tracker.call_depth() > config['recursion_depth'] + 1:
                    return True
            if 'recursion_identity' in config and config['recursion_identity']:
                if self._pypads.call_tracker.has_call_identity(accessor):
                    return True
            return False
        except Exception as e:
            return False
