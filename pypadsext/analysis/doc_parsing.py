def doc(self, *args, _pypads_wrappe,
             _pypads_context,
             _pypads_mapped_by,
             _pypads_callback, **kwargs):

    doc = _pypads_wrappe.__doc__

    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()

    pads.api.log_mem_artifact(_pypads_wrappe.__name__ + ".__doc__", doc)

    output = _pypads_callback(*args, **kwargs)
    return output
