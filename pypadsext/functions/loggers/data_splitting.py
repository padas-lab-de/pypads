from types import GeneratorType
from typing import Tuple, Iterable

from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.loggers.base_logger import LoggingFunction


def split_output_inv(result, fn=None):
    # function that looks into the output of the custom splitter
    split_info = dict()

    # Flag to check whether the outputs of the splitter are indices (one dimensional Iterable)
    indices = True
    if isinstance(result, Tuple):
        n_output = len(result)
        for a in result:
            if isinstance(a, Iterable):
                for row in a:
                    if isinstance(row, Iterable):
                        indices = False
                        break

        if n_output > 3:
            if indices:
                Warning(
                    'The splitter function return values are ambiguous (more than train/test/validation splitting).'
                    'Decision tracking might be inaccurate')
                split_info.update({'set_{}'.format(i): a for i, a in enumerate(result)})
                split_info.update({"decision_track": False})
            else:
                Warning("The output of the splitter is not indices, Decision tracking might be inaccurate.")
                if "sklearn" in fn.__module__:
                    split_info.update({'Xtrain': result[0], 'Xtest': result[1], 'ytrain': result[2],
                                       'ytest': result[3]})
                    split_info.update({"decision_track": True})
                else:
                    split_info.update({'output_{}'.format(i): a for i, a in enumerate(result)})
                    split_info.update({"decision_track": False})
        else:
            if indices:
                names = ['train', 'test', 'val']
                i = 0
                while i < n_output:
                    split_info[names[i]] = result[i]
                    i += 1
                split_info.update({"decision_track": True})
            else:
                Warning("The output of the splitter is not indices, Decision tracking might be inaccurate.")
                split_info.update({'output_{}'.format(i): a for i, a in enumerate(result)})
                split_info.update({"decision_track": False})
    else:
        Warning("The splitter has a single output. Decision tracking might be inaccurate.")
        split_info.update({'output_0': result})
        split_info.update({"decision_track": True})
    return split_info


class SplitsTracker(LoggingFunction):
    """
    Function that tracks data splits
    """

    def call_wrapped(self, ctx, *args, _pypads_env: LoggingEnv, _args, _kwargs, **_pypads_hook_params):
        """

        :param ctx:
        :param args:
        :param _pypads_result:
        :param kwargs:
        :return:
        """
        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads

        pads: PyPadrePads = get_current_pads()

        result = _pypads_env.callback(*_args, **_kwargs)

        if isinstance(result, GeneratorType):
            def generator():
                num = -1
                for r in result:
                    num += 1
                    pads.cache.run_add("current_split", num)
                    split_info = split_output_inv(r, fn=_pypads_env.callback)
                    pads.cache.run_add(num, {"split_info": split_info})
                    yield r
        else:
            def generator():
                split_info = split_output_inv(result, fn=_pypads_env.callback)
                pads.cache.run_add("current_split", 0)
                pads.cache.run_add(0, {"split_info": split_info})

                return result

        return generator()
