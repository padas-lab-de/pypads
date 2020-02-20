class ValidateTrainTestSplits:
    """
    This class does a basic validation on the training and testing split.
    It checks whether there are overlapping indices in the train, test or validation data
    """

    def validate(self, train_idx, test_idx, val_idx, dataset):
        """
        Validates the dataset split of training, testing and validation
        :param train_idx: The training indices
        :param test_idx: The testing indices
        :param val_idx: The validation indices
        :param dataset: The dataset matrix
        :return: Bool, True: Successful Validation False: Validation failed
        """

        if dataset is None:
            return False

        if train_idx is None:
            return False

        if test_idx is not None and len(set(train_idx).intersection(set(test_idx))) > 0:
            return False

        if val_idx is not None and len(set(train_idx).intersection(set(val_idx))) > 0:
            return False

        if val_idx is not None and test_idx is not None and len(set(val_idx).intersection(set(test_idx))) > 0:
            return False

        return True
