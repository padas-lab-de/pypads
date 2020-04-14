import unittest


def more_experiment(i):
    print("I'm a deep even module level experiment iteration " + str(i))
    return "I'm a deep even return value iteration " + str(i)


def sub_experiment(i):
    print("I'm a deep module level experiment iteration " + str(i))
    if i % 2 == 0:
        more_experiment(i)
    return "I'm a deep return value iteration " + str(i)


def experiment():
    print("I'm an module level experiment")
    for i in range(0, 10):
        sub_experiment(i)
    return "I'm a return value."


class PypadsHookTest(unittest.TestCase):

    def test_api(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads()

        global experiment
        experiment = tracker.api.track(experiment, events=["pypads_fit"])

        global sub_experiment
        sub_experiment = tracker.api.track(sub_experiment, events=["pypads_fit"])

        global more_experiment
        more_experiment = tracker.api.track(more_experiment, events=["pypads_fit"])

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        import mlflow
        # TODO
        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        mlflow.end_run()
