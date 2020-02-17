import numpy as np
from sklearn.datasets import make_classification, make_moons, make_circles


def moons():
    return make_moons(noise=0.3, random_state=0)


def circles():
    return make_circles(noise=0.2, factor=0.5, random_state=1)


def linearly_separable():
    X, y = make_classification(n_features=2, n_redundant=0, n_informative=2,
                               random_state=1, n_clusters_per_class=1)
    rng = np.random.RandomState(2)
    X += 2 * rng.uniform(size=X.shape)
    return X, y
