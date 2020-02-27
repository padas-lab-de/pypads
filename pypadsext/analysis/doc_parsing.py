import os
from logging import warning

from pypadsext.util import is_package_available


def tag_extraction():
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()
    docs = pads.cache.get("doc_map")
    corpus = " ".join([doc for name, doc in docs.items()])

    import re
    corpus = re.sub('[\s]+', ' ', corpus)
    corpus = re.sub('[\t]+', '', corpus)
    corpus = re.sub('[\n]+', '', corpus)
    pat = re.compile(r'([A-Z][^\[\]\+\<\>\-\.!?]*[\.!?])', re.M)
    corpus = " ".join(pat.findall(corpus))

    if is_package_available("spacy"):
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
        pads.cache.run_add("doc_named_entities", ents)
        find_rdf_by_label()

    elif is_package_available("nltk"):
        # TODO https://towardsdatascience.com/named-entity-recognition-with-nltk-and-spacy-8c4a7d88e7da
        pass


query = """SELECT ?item ?itemLabel
WHERE { 
  ?item rdfs:label ?itemLabel. 
  FILTER(REGEX(LCASE(?itemLabel), "%s"@en)). 
}
LIMIT 10"""


def find_rdf_by_label():
    import re
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()
    if pads.cache.run_exists("doc_named_entities"):
        ents = pads.cache.run_get("doc_named_entities")
        regex = ""
        init = True
        for entity in ents:
            entity = str(entity).lower()
            if init:
                regex = re.escape(entity)
                init = False
            else:
                regex += "|.*" + re.escape(entity) + ".*"
        label_query = query % regex
        print(label_query)
        # TODO send query to sparql endpoint (This will be really slow on most endpoints if some data is in there)
    else:
        warning("Couldn't extract any rdf links because named entities are not in cache.")


def link_rdf(self, *args, _pypads_wrappe,
             _pypads_context,
             _pypads_mapped_by,
             _pypads_callback, **kwargs):
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()
    pads.api.register_post_fn("find_labeled_sparql", find_rdf_by_label)


def doc(self, *args, _pypads_wrappe,
        _pypads_context,
        _pypads_mapped_by,
        _pypads_callback, **kwargs):
    doc_str = _pypads_wrappe.__doc__

    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()
    pads.api.register_post_fn("tag_extraction", tag_extraction)

    doc_map = {}
    if not pads.cache.exists("doc_map"):
        pads.cache.add("doc_map", doc_map)
    else:
        doc_map = pads.cache.get("doc_map")

    if doc_str:
        name = os.path.join(_pypads_context.__name__, _pypads_wrappe.__name__ + ".__doc__")
        pads.api.log_mem_artifact(name, doc_str)
        doc_map[name] = doc_str

        if _pypads_context.__doc__:
            name = os.path.join(_pypads_context.__name__,
                                _pypads_context.__name__ + ".__doc__")
            pads.api.log_mem_artifact(name, _pypads_context.__doc__)
            doc_map[name] = _pypads_context.__doc__

    pads.cache.add("doc_map", doc_map)
    output = _pypads_callback(*args, **kwargs)
    return output
