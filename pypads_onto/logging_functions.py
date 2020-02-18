from pypads import logging_functions

original_log_init = logging_functions.log_init


def ontology(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by,
             _pypads_callback, **kwargs):
    """
        Function logging the loaded dataset.
        :param self: Wrapper library object
        :param args: Input args to the real library call
        :param _pypads_wrappe: _pypads provided - wrapped library object
        :param _pypads_mapped_by: _pypads provided - wrapped library package
        :param _pypads_item: _pypads provided - wrapped function name
        :param _pypads_fn_stack: _pypads provided - stack of all the next functions to execute
        :param kwargs: Input kwargs to the real library call
        :return:
        """
    import inspect
    if inspect.isclass(self):
        cls = self
    else:
        cls = self.__class__

    cls_doc = cls.__doc__

    result = original_log_init(self, *args, _pypads_wrappe=_pypads_wrappe, _pypads_context=_pypads_context,
                               _pypads_mapped_by=_pypads_mapped_by,
                               _pypads_callback=_pypads_callback, **kwargs)
    return result


logging_functions.log_init = ontology
