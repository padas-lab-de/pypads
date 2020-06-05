from pypads import logger


def make_hook_applicable_filter(hook, ctx, mapping):
    """
    Create a filter to check if hook is applicable
    :param hook:
    :param ctx:
    :param mapping:
    :return:
    """

    def hook_applicable_filter(name):
        if hasattr(ctx, name):
            try:
                fn = getattr(ctx, name)
                return hook.is_applicable(mapping=mapping, fn=fn)
            except RecursionError as re:
                logger.error("Recursion error on '" + str(
                    ctx) + "'. This might be because __get_attr__ is being wrapped. " + str(re))
        else:
            logger.warning("Can't access attribute '" + str(name) + "' on '" + str(ctx) + "'. Skipping.")
        return False

    return hook_applicable_filter


def find_applicable_hooks(context, mapping):
    if mapping.hooks:
        for hook in mapping.hooks:
            for name in list(filter(make_hook_applicable_filter(hook, context, mapping), dir(context))):
                yield name, context, mapping
