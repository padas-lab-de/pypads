from collections.__init__ import OrderedDict

from pypads import logger
from pypads.app.call import CallAccessor, CallId, Call


# class CallMapping(CallAccessor):
#
#     def __init__(self, instance, _pypads_context, _pypads_wrappee, mapping):
#         super().__init__(instance, _pypads_context, _pypads_wrappee)
#         self._mapping = mapping
#
#     @property
#     def mapping(self):
#         return self._mapping


class CallTracker:
    """
    This class tracks the number of execution per instance of an object.
    """

    def __init__(self, pads):
        self._pads = pads
        self._call_stack = []

    def instance_call_number(self, accessor):
        function_calls: OrderedDict = self.function_call_dict(accessor.function_id)
        instance_id = accessor.instance_id

        call_items = list(function_calls.items())
        for instance_number in range(0, len(call_items)):
            # noinspection PyUnresolvedReferences
            key, value = call_items[instance_number]
            if key == instance_id:
                return instance_number
        return 0

    @property
    def call_stack(self):
        return self._call_stack

    def call_depth(self):
        return len(self._call_stack)

    def call_number(self, accessor: CallAccessor):
        """
        Get the number of calls of given call accessor
        :param accessor:
        :return:
        """
        return len(self.calls(accessor))

    def make_call_id(self, accessor: CallAccessor) -> CallId:
        """
        Returns the current call id. The id is built from: process_id, thread_id, defining_ctx_name, self_number/id,
        wrapped_fn_name, call_number
        :param accessor:
        :return:
        """
        return CallId(accessor.instance, accessor.context, accessor.wrappee, self.instance_call_number(accessor),
                      self.call_number(accessor))

    def current_call_number(self):
        """
        Get the current call number
        :return:
        """
        call = self._call_stack[-1]
        return self.call_number(call.accessor)

    def current_call(self):
        """
        Get the call_id of the current call
        :return:
        """
        return self._call_stack[-1] if len(self._call_stack) > 0 else None

    def current_process(self):
        return str(self._call_stack[-1].call_id.process) + "." + str(self._call_stack[-1].call_id.thread)

    def call_objects(self):
        """
        Get all call objects which are stored in our tracker.
        :return:
        """
        # Add call_objects if not exists in cache
        if not self._pads.cache.run_exists("call_objects"):
            self._pads.cache.run_add("call_objects", {})
        return self._pads.cache.run_get("call_objects")

    def function_call_dict(self, function_id) -> OrderedDict:
        call_objects = self.call_objects()
        if function_id not in call_objects:
            call_objects[function_id] = OrderedDict()
        return call_objects[function_id]

    def calls(self, accessor: CallAccessor):
        """
        Get all calls of given call accessor.
        :param accessor:
        :return:
        """
        instance_id = accessor.instance_id
        function_id = accessor.function_id

        function_calls = self.function_call_dict(function_id)
        if instance_id not in function_calls:
            function_calls[instance_id] = []

        return function_calls[instance_id]

    def has_call_identity(self, accessor: CallAccessor):
        for stored in self._call_stack:
            if stored.call_id.is_call_identity(accessor):
                return True
        return False

    def add(self, call: Call):
        """
        When a new call is triggered execute that function. This should be the first logging function called in each
        logging function stack.
        :return: A dict for holding information about the call.
        """
        self._call_stack.append(call)

        calls = self.calls(call.call_id)
        calls.append(call)
        return call

    def finish(self, call):
        if call in self._call_stack:
            self._call_stack.remove(call)
            # TODO clear memory in call_objects?
        else:
            logger.error("Tried to finish call which is not on the stack. " + str(call))


def add_call(accessor):
    from pypads.app.pypads import get_current_pads
    pads = get_current_pads()
    call = Call(call_id=pads.call_tracker.make_call_id(accessor))
    return pads.call_tracker.add(call)


def finish_call(call):
    from pypads.app.pypads import get_current_pads
    pads = get_current_pads()
    pads.call_tracker.finish(call)
