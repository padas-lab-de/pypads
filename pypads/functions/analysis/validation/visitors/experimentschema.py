from .schema import Attribute, Schema, ListAttribute, AlgorithmSchema


default_pipeline_schema = Schema(
    {
        "steps": ListAttribute("steps", "The steps", False, [
            {
                "docs": Attribute("docs", "Docstring", True, str),
                "algorithm": Attribute("algorithm", "The name of the used algorithm", False, str)
            },
            AlgorithmSchema()
        ]),
        "docs": Attribute("docs", "Docstring", True, str)
    }
)
