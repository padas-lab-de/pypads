events = {}


class EventType:
    """
    Pypads event type. Every event type triggers multiple logging functions to be executed.
    Events are triggered by hooks.
    """

    def __init__(self, name, description):
        """
        Constructor for an event.
        :param name: Name of the event.
        :param description: Description of the event.
        """
        self._name = name
        self._description = description
        events[self._name] = self

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description


def init_events():
    if not all([a.name in events for a in DEFAULT_EVENTS]):
        raise Exception("There seems to be an issues with adding the anchors")


def get_event(name):
    if name not in events:
        return None
    return events.get(name)


# TODO maybe change to enum
DEFAULT_EVENTS = [EventType("parameters", "Track the parameters for given model."),
                  EventType("output", "Track the output of the function."),
                  EventType("input", "Track the input of the function."),
                  EventType("hardware", "Track current hardware load on function execution."),
                  EventType("metric", "Track a metric."),
                  EventType("autolog", "Activate mlflow autologging."),
                  EventType("pipeline", "Track a pipeline step."),
                  EventType("log", "Log the call to console."),
                  EventType("init", "Log the tracked class init to console.")]
