from typing import Optional, List

from pydantic import BaseModel, root_validator

from pypads.model.models import IdBasedEntry, Entry


class ContextModel(Entry):
    reference: str = ...  # Path to the context e.g.: sklearn.tree.tree.DecisionTree
    category: str = "Context"

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


class CallModel(IdBasedEntry):
    category: str = "Call"
    call_id: CallIdModel = ...  # Id of the call
    finished: bool = False

    class Config:
        orm_mode = True


class LoggerCallModel(IdBasedEntry):
    """
    Holds meta data about a logger execution
    """
    failed: Optional[str] = None
    execution_time: Optional[float] = ...

    created_by: str = ...  # reference to LoggerModel
    output: Optional[str] = ...  # reference to OutputModel of the logger
    name: str = "Call"

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
    category: str = "InjectionLoggerCall"
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
    category: str = "MultiInjectionLoggerCall"

    class Config:
        orm_mode = True
