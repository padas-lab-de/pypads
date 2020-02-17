def evaluate(clf, X_test, y_test):
    score = clf.score(X_test, y_test)
    return score
