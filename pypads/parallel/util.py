import io
import pickle


def _pickle_tuple(*args):
    with io.BytesIO() as file:
        pickle.dump(tuple(args), file)
        file.seek(0)
        return file.read()


def _cloudpickle_tuple(*args):
    from joblib.externals.cloudpickle import dumps
    return dumps(tuple(args))
