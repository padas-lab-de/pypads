import os
import re

from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.loggers.base_logger import LoggingFunction

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


class Doc(LoggingFunction):

    def __pre__(self, ctx, *args, _pypads_env: LoggingEnv,**kwargs):

        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()

        pads.api.register_post_fn("tag_extraction", tag_extraction)

        doc_map = {}
        if not pads.cache.exists("doc_map"):
            pads.cache.add("doc_map", doc_map)
        else:
            doc_map = pads.cache.get("doc_map")

        if _pypads_env.call.call_id.wrappee.__doc__:
            name = os.path.join(_pypads_env.call.to_folder(),
                                _pypads_env.call.call_id.wrappee.__name__ + ".__doc__")
            if not pads.api.is_intermediate_run():
                pads.api.log_mem_artifact(name, _pypads_env.call.call_id.wrappee.__doc__)
            doc_map[name] = _pypads_env.call.call_id.wrappee.__doc__

        if _pypads_env.call.call_id.context.container.__doc__:
            name = os.path.join(_pypads_env.call.to_folder(),
                                _pypads_env.call.call_id.context.container.__name__ + ".__doc__")
            if not pads.api.is_intermediate_run():
                pads.api.log_mem_artifact(name, _pypads_env.call.call_id.context.container.__doc__)
            doc_map[name] = _pypads_env.call.call_id.context.container.__doc__

        # Add ctx name to doc_map for named entity searching
        doc_map[_pypads_env.call.call_id.context.container.__name__ + "_exists"] = "The " + name_to_words(
            _pypads_env.call.call_id.context.container.__name__) + " exists."
        doc_map[_pypads_env.call.call_id.wrappee.__name__ + "_exists"] = "The " + name_to_words(
            _pypads_env.call.call_id.wrappee.__name__) + " exists."
        doc_map[_pypads_env.call.call_id.wrappee.__name__ + "_is_in"] = "The " + name_to_words(
            _pypads_env.call.call_id.wrappee.__name__) + " is in " + name_to_words(_pypads_env.call.call_id.context.container.__name__) + "."
        # !Add ctx name to doc_map for named entity searching
        pads.cache.add("doc_map", doc_map)
