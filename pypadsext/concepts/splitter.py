import numpy as np
from pypadre.core.model.dataset.dataset import Dataset
from pypadre.core.model.split.split import Split
from pypadre.core.util.utils import unpack


def default_split(ctx, strategy="random", test_ratio=0.25, random_seed=None, val_ratio=0,
          n_folds=3, shuffle=True, stratified=None, indices=None, index=None):
    (data, y) = unpack(ctx, "data", ("targets", None))
    """
        The splitter creates index arrays into the dataset for different splitting startegies. It provides an iterator
        over the different splits.

        Currently the following splitting strategies are supported:
         - random split (stratified / non-stratified). If no_shuffle is true, the order will not be changed.
         - cross validation (stratified / non-stratified)"
         - explicit - expects an explicit split given as parameter indices = (train_idx, val_idx, test_idx)
         - function - expects a function taking as input the dataset and performing the split.
         - none - there will be no splitting. only a training set will be provided

         Options:
         ========
         - strategy={"random"|"cv"|"explicit"|"none"/None} splitting strategy, default random
         - test_ratio=float[0:1]   ratio of test dataset, default 0.25
         - val_ratio=float[0:1]    ratio of the validation test (taken from the training set), default 0
         - n_folds=int             number of folds when selecting cv strategies, default 3. smaller than dataset size
         - random_seed=int         seed for the random generator or None if no seeding should be done
         - stratified={True|False|None} True, if splits should consider class stratification. If None, than stratification
                                   is activated when there are targets (default). Otherwise, stratification strategies
                                    is taking explicitly into account
         - shuffle={True|False} indicates, whether shuffling the data is allowed.
         - indices = [(train, validation, test)] a list of tuples with three index arrays in the dataset.
                                   Every index array contains
                                   the row index of the datapoints contained in the split
        """
    if isinstance(data, Dataset):
        n = data.size[0]

    # TODO FIXME
    # first create index array and random state vector
    # n = data.size

    # TODO FIXME usage?
    # stratified = self._stratified
    if stratified is None:
        stratified = y is not None
    else:
        if stratified and y is None:
            stratified = False

    if random_seed is None:
        from pypadre.core.util.random import padre_seed
        random_seed = padre_seed
    r = np.random.RandomState(random_seed)
    idx = np.arange(n)

    def splitting_iterator():
        num = -1
        # now apply splitting strategy
        # todo s: time aware cross validation, stratified splits,
        # Todo do sanity checks that indizes do not overlap
        if strategy is None:
            num += 1
            yield Split(run=run, num=++num, train_idx=idx, test_idx=None, val_idx=None, component=component,
                        predecessor=predecessor)
        elif strategy == "explicit":
            for i in indices:
                train, val, test = i
                num += 1
                yield Split(run=run, num=num, train_idx=train, test_idx=test, val_idx=val, component=component,
                            predecessor=predecessor)
        elif strategy == "random":
            if shuffle:  # Reshuffle every "fold"
                r.shuffle(idx)
            n_tr = int(n * (1.0 - test_ratio))
            train, test = idx[:n_tr], idx[n_tr:]
            num += 1
            if val_ratio > 0:  # create a validation set out of the test set
                n_v = int(len(train) * val_ratio)
                yield Split(run=run, num=num, train_idx=train[:n_v], test_idx=test, val_idx=train[n_v:],
                            component=component, predecessor=predecessor)
            else:
                yield Split(run=run, num=num, train_idx=train, test_idx=test, val_idx=None, component=component,
                            predecessor=predecessor)
        elif strategy == "cv":
            if stratified:
                # StratifiedKfold implementation of sklearn
                y = data.targets()
                classes_, y_idx, y_inv, y_counts = np.unique(y, return_counts=True, return_index=True,
                                                             return_inverse=True)
                n_classes = len(y_idx)
                _, class_perm = np.unique(y_idx, return_inverse=True)
                y_encoded = class_perm[y_inv]
                min_groups = np.min(y_counts)
                if np.all(n_folds > y_counts):
                    raise ValueError("n_folds=%d cannot be greater than the"
                                     " number of members in each class."
                                     % (n_folds))
                if n_folds > min_groups:
                    raise Warning("The least populated class in y has only %d"
                                  " members, which is less than n_splits=%d." % (min_groups, n_folds))
                y_order = np.sort(y_encoded)
                allocation = np.asarray([np.bincount(y_order[i::n_folds], minlength=n_classes)
                                         for i in range(n_folds)])
                test_folds = np.empty(len(y), dtype='i')
                for k in range(n_classes):
                    folds_for_class = np.arange(n_folds).repeat(allocation[:, k])
                    if shuffle:
                        r.shuffle(folds_for_class)
                    test_folds[y_encoded == k] = folds_for_class

                for i in range(n_folds):
                    num += 1
                    test_index = test_folds == i
                    train_idx = idx[np.logical_not(test_index)]
                    test_idx = idx[test_index]
                    yield Split(run=run, num=num, train_idx=train_idx, test_idx=test_idx, val_idx=None, component=component,
                                predecessor=predecessor)
            else:

                if shuffle:
                    r.shuffle(idx)
                for i in range(n_folds):
                    n_te = i * int(n / n_folds)
                    test = idx[n_te: n_te + int(n / n_folds)]
                    train = np.asarray(list(set(idx) - set(test)))
                    # The test array can be seen as a non overlapping sub array of size n_te moving from start to end
                    n_te = i * int(n / n_folds)
                    test = np.asarray(range(n_te, n_te + int(n / n_folds)))

                    # if the test array exceeds the end of the array wrap it around the beginning of the array
                    test = np.mod(test, n)

                    # The training array is the set difference of the complete array and the testing array
                    train = np.asarray(list(set(idx) - set(test)))

                    num += 1
                    if val_ratio > 0:  # create a validation set out of the test set
                        n_v = int(len(train) * val_ratio)
                        yield Split(run=run, num=num, train_idx=train[:n_v], test_idx=test, val_idx=train[n_v:],
                                    component=component, predecessor=predecessor)
                    else:
                        yield Split(run=run, num=num, train_idx=train, test_idx=test, val_idx=None, component=component,
                                    predecessor=predecessor)

        elif strategy == "index":
            # If a list of dictionaries are given to the experiment as indices, pop each one out and return
            for i in range(len(index)):
                train = index[i].get('train', None)
                if train is not None:
                    train = np.array(train)

                test = index[i].get('test', None)
                if test is not None:
                    test = np.array(test)

                val = index[i].get('val', None)
                if val is not None:
                    val = np.array(val)
                num += 1
                yield Split(run=run, num=num, train_idx=train, test_idx=test, val_idx=val, component=component,
                            predecessor=predecessor)

        else:
            raise ValueError(f"Unknown splitting strategy {strategy}")

    return splitting_iterator()