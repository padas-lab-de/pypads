from typing import Optional, List, Union

import pydantic
from pydantic import BaseModel

from pypads.model.logger_output import FallibleModel
from pypads.model.models import BaseStorageModel, EntryModel, ResultType, ProvenanceModel, IdReference


class ContextModel(EntryModel):
    """
    A reference to a class / model
    """
    reference: str = ...  # Path to the context e.g.: sklearn.tree.tree.DecisionTree
    category: str = "Context"
    storage_type: Union[ResultType, str] = "context"

    class Config:
        orm_mode = True


class FunctionReferenceModel(BaseModel):
    """
    A reference to a function on a class
    """
    fn_name: str = ...  # Function name on the given context e.g.: sklearn.tree.tree.DecisionTree.fit
    context: ContextModel = ...  # Context on which function was defined

    class Config:
        orm_mode = True


class CallAccessorModel(FunctionReferenceModel):
    """
    A reference to a specific instance of a class
    """
    instance_id: int = ...  # Instance id of the instance on which a call was done

    class Config:
        orm_mode = True


class CallIdModel(CallAccessorModel):
    """
    The call id containing all references and process, thread, instance_number and call_number information
    """
    process: int = ...  # Process of the call
    thread: int = ...  # Thread of the call
    instance_number: int = ...  # Number of the call on instance
    call_number: int = ...  # Plain number of the call

    class Config:
        orm_mode = True


class CallModel(BaseStorageModel):
    """
    A single call containing the call_id and a finished state to represent a function call.
    """
    category: str = "Call"
    call_id: Optional[CallIdModel] = ...  # Id of the call
    finished: bool = False
    storage_type: Union[ResultType, str] = "Call"

    class Config:
        orm_mode = True


class LoggerCallModel(ProvenanceModel, BaseStorageModel, FallibleModel):
    """
    Holds meta data about a logger execution. This can be by api, setup, teardown or by injection/mapping file.
    """
    execution_time: Optional[float] = ...
    storage_type: Union[ResultType, str] = ResultType.logger_call
    created_by: Optional[IdReference] = ...  # reference to LoggerModel
    output: Optional[IdReference] = ...  # reference to OutputModel of the logger
    name: str = "Call"
    finished: bool = False

    class Config:
        orm_mode = True


class InjectionLoggerCallModel(LoggerCallModel):
    """
    Holds meta data about an injection/mapping file logger execution
    """
    pre_time: Optional[float] = ...
    post_time: Optional[float] = ...
    child_time: Optional[float] = ...
    original_call: CallModel = ...  # Triggered by following call
    category: str = "InjectionLoggerCall"
    execution_time: Optional[float] = None

    @pydantic.validator('execution_time', pre=True, always=True)
    def default_ts_modified(cls, v, *, values, **kwargs):
        if v is None:
            if 'pretime' in values and 'post_time' in values:
                if values['pre_time'] is not None and values['post_time'] is not None:
                    return values['pre_time'] + values['post_time']
        return v

    class Config:
        orm_mode = True


class MultiInjectionLoggerCallModel(InjectionLoggerCallModel):
    """Holds meta data about an injection logger multiple execution"""
    call_stack: List[CallModel] = ...
    pre_time: Optional[float] = 0.0
    post_time: Optional[float] = 0.0
    child_time: Optional[float] = 0.0
    category: str = "MultiInjectionLoggerCall"

    class Config:
        orm_mode = True
