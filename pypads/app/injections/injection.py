import traceback
from abc import ABCMeta, abstractmethod
from typing import Type, Union

from pydantic import BaseModel

from pypads import logger
from pypads.app.call import Call
from pypads.app.env import InjectionLoggerEnv
from pypads.app.injections.base_logger import Logger, LoggerExecutor, OriginalExecutor, env_cache
from pypads.app.injections.tracked_object import LoggerCall, FallibleMixin
from pypads.app.misc.inheritance import SuperStop
from pypads.app.misc.mixins import OrderMixin
from pypads.exceptions import NoCallAllowedError
from pypads.model.logger_call import InjectionLoggerCallModel, MultiInjectionLoggerCallModel
from pypads.model.logger_model import InjectionLoggerModel
from pypads.utils.util import inheritors


class InjectionLoggerCall(LoggerCall):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return InjectionLoggerCallModel

    def __init__(self, *args, logging_env: InjectionLoggerEnv, **kwargs):
        super().__init__(*args, original_call=logging_env.call, logging_env=logging_env, **kwargs)


class InjectionLogger(Logger, OrderMixin, SuperStop, metaclass=ABCMeta):
    """
    This is a logger which should be injected via a mapping file. It can also be injected by wrapping functions
    manually.
    """
    category: str = "InjectionLogger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not hasattr(self, "_pre"):
            self._pre = LoggerExecutor(fn=self.__pre__)
        if not hasattr(self, "_post"):
            self._post = LoggerExecutor(fn=self.__post__)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return InjectionLoggerModel

    def __pre__(self, ctx, *args,
                _logger_call, _logger_output, _args, _kwargs, **kwargs):
        """
        The function to be called before executing the log anchor. the value returned will be passed on to the __post__
        function as **_pypads_pre_return**.


        :return: _pypads_pre_return
        """
        pass

    def __post__(self, ctx, *args, _logger_call, _pypads_pre_return, _pypads_result, _logger_output, _args, _kwargs,
                 **kwargs):
        """
        The function to be called after executing the log anchor.

        :param _pypads_pre_return: the value returned by __pre__.
        :param _pypads_result: the value returned by __call_wrapped__.

        :return: the wrapped function return value
        """
        pass

    def __real_call__(self, ctx, *args, _pypads_env: InjectionLoggerEnv, _pypads_input_results,
                      _pypads_cached_results, **kwargs):
        _pypads_hook_params = _pypads_env.parameter

        reference = self.store()

        logger_call: Union[InjectionLoggerCall, FallibleMixin] = self._get_logger_call(_pypads_env)
        output = self.build_output(_pypads_env, logger_call)

        kwargs_ = {**self.static_parameters, **_pypads_hook_params}

        try:
            # Set environment information into cache
            _environment_information = {"ctx": ctx, "_args": args, "_pypads_env": _pypads_env,
                                        "_logger_call": logger_call,
                                        "_logger_output": output, "_kwargs": kwargs,
                                        "_pypads_input_results": _pypads_input_results,
                                        "_pypads_cached_results": _pypads_cached_results,
                                        "kwargs": kwargs_}
            _pypads_env.pypads.cache.run_add(env_cache(output), _environment_information)

            # Trigger pre run functions
            _pre_result, pre_time = self._pre(ctx, _pypads_env=_pypads_env,
                                              _logger_output=output,
                                              _logger_call=logger_call,
                                              _pypads_input_results=_pypads_input_results,
                                              _pypads_cached_results=_pypads_cached_results,
                                              _args=args,
                                              _kwargs=kwargs, **kwargs_)
            logger_call.pre_time = pre_time

            _environment_information.update({"_pre_result": _pre_result})

            # Trigger function itself
            _return, time = self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _logger_call=logger_call,
                                                  _logger_output=output, _args=args,
                                                  _kwargs=kwargs)
            logger_call.child_time = time

            _environment_information.update({"_pypads_result": _return})

            # Trigger post run functions
            _post_result, post_time = self._post(ctx, _pypads_env=_pypads_env,
                                                 _logger_output=output,
                                                 _pypads_pre_return=_pre_result,
                                                 _pypads_result=_return,
                                                 _logger_call=logger_call,
                                                 _pypads_input_results=_pypads_input_results,
                                                 _pypads_cached_results=_pypads_cached_results,
                                                 _args=args,
                                                 _kwargs=kwargs, **kwargs_)
            logger_call.post_time = post_time

            _environment_information.update({"_post_result": _post_result})
        except Exception as e:
            logger_call.failed = str(e)
            if output:
                output.set_failure_state(e)
            raise e
        finally:
            for fn in self.cleanup_fns(logger_call):
                fn(self, logger_call)
            self._store_results(output, logger_call)
            _pypads_env.pypads.cache.run_remove(env_cache(output))
        return self._get_return_value(_return, _post_result)

    def _get_logger_call(self, _pypads_env) -> Union[InjectionLoggerCall, FallibleMixin]:
        return InjectionLoggerCall(logging_env=_pypads_env, creator=self)

    @staticmethod
    def _get_return_value(original_return, pypads_return):
        return original_return

    def __call_wrapped__(self, ctx, *args, _pypads_env: InjectionLoggerEnv, _logger_call, _logger_output, _args,
                         _kwargs):
        """
        The real call of the wrapped function. Be carefull when you change this.
        Exceptions here will not be catched automatically and might break your workflow. The returned value will be passed on to __post__ function.

        :return: _pypads_result
        """
        _return, time = OriginalExecutor(fn=_pypads_env.callback)(*_args, **_kwargs)
        return _return, time

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        """
        Handle error for DefensiveCallableMixin
        :param args:
        :param ctx:
        :param _pypads_env:
        :param error:
        :param kwargs:
        :return:
        """
        try:
            raise error
        except NoCallAllowedError as e:

            # Call next wrapped callback if no call was allowed due to the settings or environment
            _pypads_hook_params = _pypads_env.parameter
            return self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=args, _kwargs=kwargs,
                                         **_pypads_hook_params)
        except Exception as e:
            logger.error("Logging failed for " + str(self) + ": " + str(error) + "\nTrace:\n" + traceback.format_exc())

            # Try to call the original unwrapped function if something broke
            original = _pypads_env.call.call_id.context.original(_pypads_env.callback)
            if callable(original):
                try:
                    logger.error("Trying to recover from: " + str(e))
                    out = original(ctx, *args, **kwargs)
                    logger.success("Succeeded recovering on error : " + str(e))
                    return out
                except TypeError as e:
                    logger.error("Recovering failed due to: " + str(
                        e) + ". Trying to call without passed ctx. This might be due to an error in the wrapping.")
                    out = original(*args, **kwargs)
                    logger.success("Succeeded recovering on error : " + str(e))
                    return out
            else:

                # Original function was not accessible
                raise Exception("Couldn't fall back to original function for " + str(
                    _pypads_env.logger_call.call_id.context.original_name(_pypads_env.callback)) + " on " + str(
                    _pypads_env.logger_call.call_id.context) + ". Can't recover from " + str(error))


class OutputModifyingMixin(InjectionLogger, SuperStop, metaclass=ABCMeta):

    @staticmethod
    def _get_return_value(original_return, pypads_return):
        return pypads_return


class DelayedResultsMixin(Logger, SuperStop, metaclass=ABCMeta):

    @staticmethod
    @abstractmethod
    def finalize_output(pads, logger_call, output, *args, **kwargs):
        raise NotImplementedError("Called delayed results logger without implemented finalize_output.")

    def _store_results(self, output, logger_call):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        pads.cache.run_add(id(self), {'id': id(self), 'logger_call': logger_call, 'output': output})

        def finalize(pads, *args, **kwargs):
            data = pads.cache.run_get(id(self))
            logger_call = data.get('logger_call')
            output = data.get('output')
            self.finalize_output(pads, *args, logger_call=logger_call, output=output, **kwargs)
            logger_call.finish()
            logger_call.store()

        pads.api.register_teardown_utility('{}_clean_up'.format(self.__class__.__name__), finalize,
                                           error_message="Couldn't finalize output of logger {},"
                                                         "because of exception: {} \nTrace:\n{}")


class MultiInjectionLoggerCall(LoggerCall):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return MultiInjectionLoggerCallModel

    def __init__(self, *args, logging_env: InjectionLoggerEnv, **kwargs):
        super().__init__(*args, original_call=logging_env.call, logging_env=logging_env, **kwargs)
        self.call_stack = [logging_env.call]

    @property
    def last_call(self):
        return self.call_stack[-1]

    def add_call(self, call: Call):
        self.call_stack.append(call)


class MultiInjectionLogger(DelayedResultsMixin, InjectionLogger, SuperStop, metaclass=ABCMeta):
    """
    This logger gets called on function calls. It is expected to run multiple times for each experiment.
    """

    def _get_logger_call(self, _pypads_env: InjectionLoggerEnv):
        pads = _pypads_env.pypads
        if pads.cache.run_exists(id(self)):
            logger_call = pads.cache.run_get(id(self)).get('logger_call')
            logger_call.add_call(_pypads_env.call)
            return logger_call
        else:
            self.store()
            return MultiInjectionLoggerCall(logging_env=_pypads_env, creator=self)

    def build_output(self, _pypads_env: InjectionLoggerEnv, _logger_call, **kwargs):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        if pads.cache.run_exists(id(self)):
            logger_output = pads.cache.run_get(id(self)).get('output')
            logger_output.add_call_env(_pypads_env)
            return logger_output
        else:
            return super().build_output(_pypads_env, _logger_call)

    # noinspection DuplicatedCode
    def __real_call__(self, ctx, *args, _pypads_env: InjectionLoggerEnv, _pypads_input_results,
                      _pypads_cached_results, **kwargs):
        _pypads_hook_params = _pypads_env.parameter

        logger_call: Union[MultiInjectionLoggerCall, InjectionLoggerCallModel, FallibleMixin] = self._get_logger_call(
            _pypads_env)
        output = self.build_output(_pypads_env, logger_call)

        kwargs_ = {**self.static_parameters, **_pypads_hook_params}

        try:
            # Set environment information into cache
            _environment_information = {"ctx": ctx,
                                        "_args": args, "_pypads_env": _pypads_env, "_logger_call": logger_call,
                                        "_logger_output": output, "_kwargs": kwargs,
                                        "_pypads_input_results": _pypads_input_results,
                                        "_pypads_cached_results": _pypads_cached_results,
                                        "kwargs": kwargs_}
            _pypads_env.pypads.cache.run_add(env_cache(output), _environment_information)

            # Trigger pre run functions
            _pre_result, pre_time = self._pre(ctx, _pypads_env=_pypads_env,
                                              _logger_output=output,
                                              _logger_call=logger_call,
                                              _pypads_input_results=_pypads_input_results,
                                              _pypads_cached_results=_pypads_cached_results,
                                              _args=args,
                                              _kwargs=kwargs, **kwargs_)
            logger_call.pre_time += pre_time

            _environment_information.update({"_pre_result": _pre_result})

            # Trigger function itself
            _return, time = self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _logger_call=logger_call,
                                                  _logger_output=output, _args=args, _kwargs=kwargs)
            logger_call.child_time += time

            _environment_information.update({"_pypads_result": _return})

            # Trigger post run functions
            _post_result, post_time = self._post(ctx, _pypads_env=_pypads_env,
                                                 _logger_output=output,
                                                 _pypads_pre_return=_pre_result,
                                                 _pypads_result=_return,
                                                 _logger_call=logger_call,
                                                 _pypads_input_results=_pypads_input_results,
                                                 _pypads_cached_results=_pypads_cached_results,
                                                 _args=args,
                                                 _kwargs=kwargs, **{**self.static_parameters, **_pypads_hook_params})
            logger_call.post_time += post_time

            _environment_information.update({"_post_result": _post_result})
        except Exception as e:
            logger_call.failed = str(e)
            if output:
                output.set_failure_state(e)
            raise e
        finally:
            for fn in self.cleanup_fns(logger_call):
                fn(self, logger_call)
            self._store_results(output, logger_call)
            _pypads_env.pypads.cache.run_remove(env_cache(output))
        return self._get_return_value(_return, _post_result)


def logging_functions():
    """
    Find all injection functions defined in our imported context.
    :return:
    """
    return inheritors(InjectionLogger)
