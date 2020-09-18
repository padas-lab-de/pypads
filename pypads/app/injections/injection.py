import traceback
from abc import ABCMeta, abstractmethod
from typing import Type

from pydantic import BaseModel, HttpUrl

from pypads import logger
from pypads.app.call import Call
from pypads.app.env import InjectionLoggerEnv
from pypads.app.injections.base_logger import LoggerCall, Logger, LoggerExecutor, OriginalExecutor
from pypads.app.misc.mixins import OrderMixin, NoCallAllowedError
from pypads.arguments import ontology_uri
from pypads.model.logger_call import InjectionLoggerCallModel, MultiInjectionLoggerCallModel
from pypads.model.logger_model import InjectionLoggerModel
from pypads.utils.util import inheritors


class InjectionLoggerCall(LoggerCall):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return InjectionLoggerCallModel

    def __init__(self, *args, logging_env: InjectionLoggerEnv, **kwargs):
        super().__init__(*args, original_call=logging_env.call, logging_env=logging_env, **kwargs)


class InjectionLogger(Logger, OrderMixin, metaclass=ABCMeta):
    is_a: HttpUrl = f"{ontology_uri}injection-logger"

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

    def __real_call__(self, ctx, *args, _pypads_env: InjectionLoggerEnv, **kwargs):
        _pypads_hook_params = _pypads_env.parameter

        self.store()

        logger_call = InjectionLoggerCall(logging_env=_pypads_env, created_by=self)
        output = self.build_output(_pypads_env)

        try:
            # Trigger pre run functions
            _pre_result, pre_time = self._pre(ctx, _pypads_env=_pypads_env,
                                              _logger_output=output,
                                              _logger_call=logger_call,
                                              _args=args,
                                              _kwargs=kwargs, **{**self.static_parameters, **_pypads_hook_params})
            logger_call.pre_time = pre_time

            # Trigger function itself
            _return, time = self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _logger_call=logger_call,
                                                  _logger_output=output, _args=args,
                                                  _kwargs=kwargs)
            logger_call.child_time = time

            # Trigger post run functions
            _post_result, post_time = self._post(ctx, _pypads_env=_pypads_env,
                                                 _logger_output=output,
                                                 _pypads_pre_return=_pre_result,
                                                 _pypads_result=_return,
                                                 _logger_call=logger_call,
                                                 _args=args,
                                                 _kwargs=kwargs, **{**self.static_parameters, **_pypads_hook_params})
            logger_call.post_time = post_time
        except Exception as e:
            logger_call.failed = str(e)
            if output:
                output.set_failure_state(e)
            raise e
        finally:
            for fn in self.cleanup_fns(logger_call):
                fn(self, logger_call)
            if output:
                logger_call.output = output.store()
            logger_call.store()
        return _return

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

                # Original function was not accessiblete
                raise Exception("Couldn't fall back to original function for " + str(
                    _pypads_env.call.call_id.context.original_name(_pypads_env.callback)) + " on " + str(
                    _pypads_env.call.call_id.context) + ". Can't recover from " + str(error))


class MultiInjectionLoggerCall(LoggerCall):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return MultiInjectionLoggerCallModel

    def __init__(self, *args, logging_env: InjectionLoggerEnv, **kwargs):
        super().__init__(*args, original_call=logging_env.call, logging_env=logging_env, **kwargs)
        self.call_stack = [logging_env.call]

    def add_call(self, call: Call):
        self.call_stack.append(call)


class MultiInjectionLogger(InjectionLogger):
    """
    This logger gets called on function calls. It is expected to run multiple times for each experiment.
    """
    is_a: HttpUrl = f"{ontology_uri}multi-injection-logger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return MultiInjectionLoggerCallModel

    def _get_call(self, logging_env: InjectionLoggerEnv):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        if pads.cache.run_exists(id(self)):
            logger_call = pads.cache.run_get(id(self)).get('call')
            logger_call.add_call(logging_env.call)
            return logger_call
        else:
            self.store()
            return MultiInjectionLoggerCall(logging_env=logging_env, created_by=self)

    def _get_output(self, _pypads_env):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        if pads.cache.run_exists(id(self)):
            logger_output = pads.cache.run_get(id(self)).get('output')
            logger_output.add_call_env(_pypads_env)
            return logger_output
        else:
            return self.build_output(_pypads_env)

    @staticmethod
    @abstractmethod
    def finalize_output(pads, *args, **kwargs):
        pass

    def __real_call__(self, ctx, *args, _pypads_env: InjectionLoggerEnv, **kwargs):
        _pypads_hook_params = _pypads_env.parameter

        logger_call = self._get_call(_pypads_env)
        output = self._get_output(_pypads_env)

        try:
            # Trigger pre run functions
            _pre_result, pre_time = self._pre(ctx, _pypads_env=_pypads_env,
                                              _logger_output=output,
                                              _logger_call=logger_call,
                                              _args=args,
                                              _kwargs=kwargs, **{**self.static_parameters, **_pypads_hook_params})
            logger_call.pre_time += pre_time

            # Trigger function itself
            _return, time = self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _logger_call=logger_call,
                                                  _logger_output=output, _args=args, _kwargs=kwargs)
            logger_call.child_time += time

            # Trigger post run functions
            _post_result, post_time = self._post(ctx, _pypads_env=_pypads_env,
                                                 _logger_output=output,
                                                 _pypads_pre_return=_pre_result,
                                                 _pypads_result=_return,
                                                 _logger_call=logger_call,
                                                 _args=args,
                                                 _kwargs=kwargs, **{**self.static_parameters, **_pypads_hook_params})
            logger_call.post_time += post_time
        except Exception as e:
            logger_call.failed = str(e)
            if output:
                output.set_failure_state(e)
            raise e
        finally:
            for fn in self.cleanup_fns(logger_call):
                fn(self, logger_call)
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
            pads.cache.run_add(id(self), {'call': logger_call, 'output': output})
            pads.api.register_teardown_utility('{}_clean_up'.format(self.__class__.__name__), self.finalize_output)
        return _return


class OutputInjectionLogger(InjectionLogger):
    is_a: HttpUrl = f"{ontology_uri}injection-logger"

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return InjectionLoggerModel

    def __real_call__(self, ctx, *args, _pypads_env: InjectionLoggerEnv, **kwargs):
        _pypads_hook_params = _pypads_env.parameter

        self.store()
        logger_call = InjectionLoggerCall(logging_env=_pypads_env, created_by=self)
        output = self.build_output(_pypads_env)

        try:
            # Trigger pre run functions
            _pre_result, pre_time = self._pre(ctx, _pypads_env=_pypads_env,
                                              _logger_output=output,
                                              _logger_call=logger_call,
                                              _args=args,
                                              _kwargs=kwargs, **{**self.static_parameters, **_pypads_hook_params})
            logger_call.pre_time = pre_time

            # Trigger function itself
            _return, time = self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _logger_call=logger_call,
                                                  _logger_output=output, _args=args,
                                                  _kwargs=kwargs)
            logger_call.child_time = time

            # Trigger post run functions
            _post_result, post_time = self._post(ctx, _pypads_env=_pypads_env,
                                                 _logger_output=output,
                                                 _pypads_pre_return=_pre_result,
                                                 _pypads_result=_return,
                                                 _logger_call=logger_call,
                                                 _args=args,
                                                 _kwargs=kwargs, **{**self.static_parameters, **_pypads_hook_params})
            logger_call.post_time = post_time
        except Exception as e:
            logger_call.failed = str(e)
            if output:
                output.set_failure_state(e)
            raise e
        finally:
            for fn in self.cleanup_fns(logger_call):
                fn(self, logger_call)
            if output:
                logger_call.output = output.store()
            logger_call.store()
        return _post_result


def logging_functions():
    """
    Find all injection functions defined in our imported context.
    :return:
    """
    return inheritors(InjectionLogger) + inheritors(MultiInjectionLogger)
