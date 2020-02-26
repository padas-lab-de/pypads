import os


def doc(self, *args, _pypads_wrappe,
        _pypads_context,
        _pypads_mapped_by,
        _pypads_callback, **kwargs):
    doc_str = _pypads_wrappe.__doc__

    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()
    doc_map = {}
    if not pads.cache.exists("doc_map"):
        pads.cache.add("doc_map", doc_map)
    else:
        doc_map = pads.cache.get("doc_map")

    if doc_str:
        name = os.path.join(_pypads_context.__name__, _pypads_wrappe.__name__ + ".__doc__")
        pads.api.log_mem_artifact(name, doc_str)
        pads.cache.add(name, doc_str)
        doc_map[name] = doc_str

        if _pypads_context.__doc__:
            name = os.path.join(_pypads_context.__name__,
                                _pypads_context.__name__ + ".__doc__")
            pads.api.log_mem_artifact(name, _pypads_context.__doc__)
            pads.cache.add(name, doc_str)
            doc_map[name] = doc_str

    pads.cache.add("doc_map", doc_map)
    output = _pypads_callback(*args, **kwargs)
    return output
