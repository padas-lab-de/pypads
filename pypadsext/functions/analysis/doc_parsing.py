import os
import re

from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.logging_util import get_current_call_folder

from pypadsext.util import _is_package_available


def name_to_words(label):
    label = re.sub(".*([a-z])([A-Z]).*", "\g<1> \g<2>", label)
    label = label.replace("_", " ")
    return label.replace(".", " ")


def tag_extraction():
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()
    docs = pads.cache.get("doc_map")
    corpus = " ".join([doc for name, doc in docs.items()])
    corpus = corpus
    corpus = re.sub('[\s]+', ' ', corpus)
    corpus = re.sub('[\t]+', '', corpus)
    corpus = re.sub('[\n]+', '', corpus)
    pat = re.compile(r'([a-zA-Z][^\[\]\+\<\>\-\.!?]*[\.!?])', re.M)
    corpus = " ".join(pat.findall(corpus))

    if _is_package_available("spacy"):
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(corpus)
        nouns = set()
        for chunk in doc.noun_chunks:
            if "=" not in chunk.text and "." not in chunk.text:
                nouns.add(chunk.text)
        pads.api.log_mem_artifact("doc_nouns", str(nouns))

        ents = set()
        for ent in doc.ents:
            if "=" not in ent.text and "." not in ent.text and "`" not in ent.text and "/" not in ent.text:
                ents.add(ent.text)
        pads.api.log_mem_artifact("doc_named_entities", str(ents))

    elif _is_package_available("nltk"):
        # TODO https://towardsdatascience.com/named-entity-recognition-with-nltk-and-spacy-8c4a7d88e7da
        pass


# def doc(self, *args, _pypads_wrappe,
#         _pypads_context,
#         _pypads_mapped_by,
#         _pypads_callback, **kwargs):
#
#     from pypads.base import get_current_pads
#     from pypadsext.base import PyPadrePads
#     pads: PyPadrePads = get_current_pads()
#     pads.api.register_post_fn("tag_extraction", tag_extraction)
#
#     doc_map = {}
#     if not pads.cache.exists("doc_map"):
#         pads.cache.add("doc_map", doc_map)
#     else:
#         doc_map = pads.cache.get("doc_map")
#
#     if _pypads_wrappe.__doc__:
#         name = os.path.join(_pypads_context.__name__, _pypads_wrappe.__name__ + ".__doc__")
#         pads.api.log_mem_artifact(name, _pypads_wrappe.__doc__)
#         doc_map[name] = _pypads_wrappe.__doc__
#
#     if _pypads_context.__doc__:
#         name = os.path.join(_pypads_context.__name__,
#                             _pypads_context.__name__ + ".__doc__")
#         pads.api.log_mem_artifact(name, _pypads_context.__doc__)
#         doc_map[name] = _pypads_context.__doc__
#
#     # Add ctx name to doc_map for named entity searching
#     doc_map[_pypads_context.__name__ + "_exists"] = "The " + name_to_words(_pypads_context.__name__) + " exists."
#     doc_map[_pypads_wrappe.__name__ + "_exists"] = "The " + name_to_words(_pypads_wrappe.__name__) + " exists."
#     doc_map[_pypads_wrappe.__name__ + "_is_in"] = "The " + name_to_words(
#         _pypads_wrappe.__name__) + " is in " + name_to_words(_pypads_context.__name__) + "."
#     # !Add ctx name to doc_map for named entity searching
#     pads.cache.add("doc_map", doc_map)
#     output = _pypads_callback(*args, **kwargs)
#     return output


class Doc(LoggingFunction):

    def __pre__(self, ctx, *args, **kwargs):

        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()

        pads.api.register_post_fn("tag_extraction", tag_extraction)

        doc_map = {}
        if not pads.cache.exists("doc_map"):
            pads.cache.add("doc_map", doc_map)
        else:
            doc_map = pads.cache.get("doc_map")

        if kwargs['_pypads_wrappe'].__doc__:
            name = os.path.join(get_current_call_folder(ctx, kwargs["_pypads_context"], kwargs["_pypads_wrappe"]),
                                kwargs['_pypads_wrappe'].__name__ + ".__doc__")
            pads.api.log_mem_artifact(name, kwargs['_pypads_wrappe'].__doc__)
            doc_map[name] = kwargs['_pypads_wrappe'].__doc__

        if kwargs["_pypads_context"].__doc__:
            name = os.path.join(get_current_call_folder(ctx, kwargs["_pypads_context"], kwargs["_pypads_wrappe"]),
                                kwargs["_pypads_context"].__name__ + ".__doc__")
            pads.api.log_mem_artifact(name, kwargs["_pypads_context"].__doc__)
            doc_map[name] = kwargs["_pypads_context"].__doc__

        # Add ctx name to doc_map for named entity searching
        doc_map[kwargs["_pypads_context"].__name__ + "_exists"] = "The " + name_to_words(
            kwargs["_pypads_context"].__name__) + " exists."
        doc_map[kwargs['_pypads_wrappe'].__name__ + "_exists"] = "The " + name_to_words(
            kwargs['_pypads_wrappe'].__name__) + " exists."
        doc_map[kwargs['_pypads_wrappe'].__name__ + "_is_in"] = "The " + name_to_words(
            kwargs['_pypads_wrappe'].__name__) + " is in " + name_to_words(kwargs["_pypads_context"].__name__) + "."
        # !Add ctx name to doc_map for named entity searching
        pads.cache.add("doc_map", doc_map)
