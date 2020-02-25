def _create_ctx(cache):
    ctx = dict()
    if "data" in cache:
        ctx["data"] = cache.get("data")
    if "shape" in cache:
        ctx["shape"] = cache.get("shape")
    if "targets" in cache:
        ctx["targets"] = cache.get("targets")
    return ctx
