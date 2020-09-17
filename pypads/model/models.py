import os
from typing import List, Union

from pydantic import BaseModel, Field, HttpUrl, root_validator

from pypads.arguments import ontology_uri
from pypads.utils.logging_util import FileFormats
from pypads.utils.util import persistent_hash

DEFAULT_CONTEXT = {
    "uri": "@id",
    "is_a": "@type",
    "experiment_id": {
        "@id": f"{ontology_uri}contained_in",
        "@type": f"{ontology_uri}Experiment"
    },
    "run_id": {
        "@id": f"{ontology_uri}contained_in",
        "@type": f"{ontology_uri}Run"
    },
    "created_at": {
        "@id": f"{ontology_uri}created_at",
        "@type": "http://www.w3.org/2001/XMLSchema#dateTime"
    },
    "name": {
        "@id": f"{ontology_uri}label",
        "@type": "http://www.w3.org/2001/XMLSchema#string"
    },
    "context": {
        "@id": f"{ontology_uri}relates_to",
        "@type": f"{ontology_uri}Context"
    },
    "reference": {
        "@id": f"{ontology_uri}represents",
        "@type": "http://www.w3.org/2001/XMLSchema#string"
    },
    "tracked_by": {
        "@id": f"{ontology_uri}tracked_by",
        "@type": f"{ontology_uri}LoggerCall"
    },
    "failed": {
        "@id": f"{ontology_uri}failure",
        "@type": "http://www.w3.org/2001/XMLSchema#boolean"
    }
}
default_ctx_path = None


def get_default_ctx_path():
    """
    Function to persist the default context and get it's location.
    :return:
    """
    try:
        global default_ctx_path
        if not default_ctx_path:
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
            obj = pads.schema_repository.get_object(uid=persistent_hash(str(DEFAULT_CONTEXT)))
            default_ctx_path = obj.get_artifact_path(obj.log_mem_artifact("pypads_context_default", DEFAULT_CONTEXT,
                                                                          write_format=FileFormats.json))
            obj.set_tag("pypads.schema_name", "pypads_context_default")
        return os.path.join(pads.uri, default_ctx_path + ".json")
    except ImportError:
        # Return context itself instead
        return DEFAULT_CONTEXT


class OntologyEntry(BaseModel):
    """
    Object representing an (potential) entry in a knowledge base
    """
    uri: HttpUrl = ...
    context: Union[List[str], str] = Field(alias='@context', default=None)

    @staticmethod
    def _add_context(values):
        if values['context'] is None:
            values['context'] = get_default_ctx_path()
        else:
            if isinstance(values['context'], List):
                values['context'].append(get_default_ctx_path())
            else:
                values['context'] = [get_default_ctx_path(), values['context']]
        return values

    def json(self, **kwargs):
        json = super().json(**kwargs)
        return self._add_context(json)


class TypedOntologyEntry(OntologyEntry):
    is_a: HttpUrl = ...
    uri: HttpUrl = None

    @root_validator
    def set_default_uri(cls, values):
        if values['uri'] is None:
            values['uri'] = f"{values['is_a']}#{values['uid']}"
        return values
