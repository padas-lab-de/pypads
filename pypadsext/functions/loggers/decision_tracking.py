import os
from logging import warning
from typing import Iterable

from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.logging_util import get_current_call_folder


class Decisions(LoggingFunction):
    """
    Function logging individual decisions
    """

    def __post__(self, ctx, *args, _pypads_result, **kwargs):
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

        preds = _pypads_result
        if pads.cache.run_exists("predictions"):
            preds = pads.cache.run_pop("predictions")

        # check if there is info about decision scores
        probabilities = None
        if pads.cache.run_exists("probabilities"):
            probabilities = pads.cache.run_pop("probabilities")

        # check if there exists information about the current split
        num = 0
        split_info = None
        if pads.cache.run_exists("current_split"):
            num = pads.cache.run_get("current_split")
        if pads.cache.run_exists(num):
            split_info = pads.cache.run_get(num).get("split_info", None)

        # depending on available info log the predictions
        if split_info is None:
            warning("No split information were found in the cache of the current run, "
                    "individual decision tracking might be missing Truth values, try to decorate you splitter!")
            pads.cache.run_add(num,
                               {'predictions': {str(i): {'predicted': preds[i]} for i in range(len(preds))}})
            if probabilities is not None:
                for i in pads.cache.run_get(num).get('predictions').keys():
                    pads.cache.run_get(num).get('predictions').get(str(i)).update(
                        {'probabilities': probabilities[int(i)]})
            if pads.cache.run_exists("targets"):
                try:
                    targets = pads.cache.run_get("targets")
                    if isinstance(targets, Iterable) and len(targets) == len(preds):
                        for i in pads.cache.run_get(num).get('predictions').keys():
                            pads.cache.run_get(num).get('predictions').get(str(i)).update(
                                {'truth': targets[int(i)]})
                except Exception as e:
                    warning("Could not add the truth values")
        else:
            try:
                for i, sample in enumerate(split_info.get('test')):
                    pads.cache.run_get(num).get('predictions').get(str(sample)).update({'predicted': preds[i]})

                if probabilities is not None:
                    for i, sample in enumerate(split_info.get('test')):
                        pads.cache.run_get(num).get('predictions').get(str(sample)).update(
                            {'probabilities': probabilities[i]})
            except Exception as e:
                print(e)

        name = os.path.join(get_current_call_folder(ctx, kwargs["_pypads_context"], kwargs["_pypads_wrappe"]),
                            "decisions",
                            str(id(kwargs["_pypads_callback"])))
        pads.api.log_mem_artifact(name, pads.cache.run_get(num))


class Decisions_sklearn(Decisions):
    """
    Function getting the prediction scores from sklearn estimators
    """

    def __pre__(self, ctx, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
        """

        :param ctx:
        :param args:
        :param kwargs:
        :return:
        """
        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()

        # check if the estimator computes decision scores
        probabilities = None
        if hasattr(ctx, "predict_proba"):
            try:
                probabilities = ctx.predict_proba(*args, **kwargs)
            except Exception as e:
                warning("Couldn't compute probabilities because %s" % str(e))
        elif hasattr(ctx, "_predict_proba"):
            try:
                probabilities = ctx._predict_proba(*args, **kwargs)
            except Exception as e:
                warning("Couldn't compute probabilities because %s" % str(e))

        pads.cache.run_add("probabilities", probabilities)


class Decisions_keras(Decisions):
    """
    Function getting the prediction scores from keras models
    """

    def __pre__(self, ctx, *args, **kwargs):
        """

        :param ctx:
        :param args:
        :param kwargs:
        :return:
        """
        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()

        probabilities = None
        try:
            probabilities = ctx.predict(*args, **kwargs)
        except Exception as e:
            warning("Couldn't compute probabilities because %s" % str(e))

        pads.cache.run_add("probabilities", probabilities)


class Decisions_torch(Decisions):
    """
    Function getting the prediction scores from torch models
    """

    def __post__(self, ctx, *args, _pypads_result, **kwargs):
        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()

        pads.cache.run_add("probabilities", _pypads_result.data.numpy())
        pads.cache.run_add("predictions", _pypads_result.argmax(dim=1).data.numpy())

        return super().__post__(ctx, *args, _pypads_result, **kwargs)
