import os
import subprocess

from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.functions.post_run.post_run import PostRunFunction
from pypads.functions.pre_run.pre_run import PreRunFunction
from pypads.logging_util import try_write_artifact, WriteFormats, get_base_folder
from pypads.util import local_uri_to_path, sizeof_fmt


class Dtrace(PreRunFunction):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _call(self, pads, *args, **kwargs):
        file = os.path.join(get_base_folder(), "truss.txt")
        proc = subprocess.Popen(['sudo', 'dtruss -f -p ' + str(os.getpid()) + '2> ' + file])

        class DtraceStop(PostRunFunction):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def _call(self, pads, *args, **kwargs):
                proc.kill()
                pads.api.log_artifact(file)

        pads.api.register_post("stop_dtrace", DtraceStop)
