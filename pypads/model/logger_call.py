from typing import Optional, List

from pydantic import BaseModel, HttpUrl, root_validator

from pypads.arguments import ontology_uri
from pypads.model.models import IdBasedOntologyEntry, IdBasedEntry


class ContextModel(BaseModel):
    reference: str = ...  # Path to the context e.g.: sklearn.tree.tree.DecisionTree
    is_a: str = f"{ontology_uri}Context"

    class Config:
        orm_mode = True


class FunctionReferenceModel(BaseModel):
    fn_name: str = ...  # Function name on the given context e.g.: sklearn.tree.tree.DecisionTree.fit
    context: ContextModel = ...  # Context on which function was defined

    class Config:
        orm_mode = True


class CallAccessorModel(FunctionReferenceModel):
    instance_id: int = ...  # Instance id of the instance on which a call was done

    class Config:
        orm_mode = True


class CallIdModel(CallAccessorModel):
    process: int = ...  # Process of the call
    thread: int = ...  # Thread of the call
    instance_number: int = ...  # Number of the call on instance
    call_number: int = ...  # Plain number of the call

    class Config:
        orm_mode = True


class CallModel(IdBasedOntologyEntry):
    is_a: HttpUrl = f"{ontology_uri}Call"
    call_id: CallIdModel = ...  # Id of the call
    finished: bool = False

    class Config:
        orm_mode = True


class LoggerCallModel(IdBasedOntologyEntry):
    """
    Holds meta data about a logger execution
    """
    failed: Optional[str] = None
    execution_time: Optional[float] = ...

    created_by: IdBasedEntry = ...  # reference to LoggerModel
    output: Optional[IdBasedEntry] = ...  # reference to OutputModel of the logger

    is_a: HttpUrl = f"{ontology_uri}LoggerCall"

    class Config:
        orm_mode = True


class InjectionLoggerCallModel(LoggerCallModel):
    """
    Holds meta data about an injection logger execution
    """
    pre_time: Optional[float] = ...
    post_time: Optional[float] = ...
    child_time: Optional[float] = ...
    original_call: CallModel = ...  # Triggered by following call
    is_a: HttpUrl = f"{ontology_uri}InjectionLoggerCall"
    execution_time: Optional[float] = None

    @root_validator
    def set_default_execution_time(cls, values):
        if values['execution_time'] is None:
            if values['pre_time'] is not None and values['post_time'] is not None:
                values['execution_time'] = values['pre_time'] + values['post_time']
        return values

    class Config:
        orm_mode = True


class MultiInjectionLoggerCallModel(InjectionLoggerCallModel):
    """Holds meta data about an injection logger multiple execution"""
    call_stack: List[CallModel] = ...
    pre_time: Optional[float] = 0.0
    post_time: Optional[float] = 0.0
    child_time: Optional[float] = 0.0
    is_a: HttpUrl = f"{ontology_uri}MultiInjectionLoggerCall"

    class Config:
        orm_mode = True
