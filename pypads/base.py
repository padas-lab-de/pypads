from mlflow.tracking import MlflowClient

from pypads.autolog.pypads_import import pypads_track

mlf = MlflowClient("file:/Users/weissger/.mlruns")


def track(*args, **kwargs):
    pypads_track(*args, **kwargs)
