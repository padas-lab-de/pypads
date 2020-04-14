# original_init_ = Process.__init__
#
#
# def punched_init_(self, group=None, target=None, name=None, args=(), kwargs={}):
#     if target:
#         run = mlflow.active_run()
#         if run:
#             @wraps(target)
#             def new_target(*args, _pypads=None, _pypads_active_run_id=None, _pypads_tracking_uri=None, _pypads_affected_modules=None, **kwargs):
#                 import mlflow
#                 import pypads.base
#                 pypads.base.current_pads = _pypads
#                 mlflow.set_tracking_uri(_pypads_tracking_uri)
#                 mlflow.start_run(run_id=_pypads_active_run_id)
#                 _pypads.activate_tracking(reload_warnings=False, affected_modules=_pypads_affected_modules, clear_imports=True)
#                 out = target(*args, **kwargs)
#                 # TODO find other way to not close run after process finishes
#                 if len(mlflow.tracking.fluent._active_run_stack) > 0:
#                     mlflow.tracking.fluent._active_run_stack.pop()
#                 return out
#
#             target = new_target
#             kwargs["_pypads"] = current_pads
#             kwargs["_pypads_active_run_id"] = run.info.run_id
#             kwargs["_pypads_tracking_uri"] = mlflow.get_tracking_uri()
#             kwargs["_pypads_affected_modules"] = punched_module_names
#     return original_init_(*self, group=group, target=target, name=name, args=args, kwargs=kwargs)
#
#
# Process.__init__ = punched_init_
