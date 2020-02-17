from sklearn.preprocessing import StandardScaler


def scale(ds):
    # preprocess dataset, split into training and test part
    X, y = ds
    X = StandardScaler().fit_transform(X)
    return X, y
