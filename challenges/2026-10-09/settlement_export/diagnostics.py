"""提供不依赖操作系统信号的按需 Python 调用栈快照。"""

from contextlib import contextmanager
import faulthandler
from pathlib import Path
import threading


@contextmanager
def stack_probe(output_dir, name):
    """收到请求文件的新标记后，把当前所有线程的调用栈追加到日志。"""
    output_dir = Path(output_dir)
    stack_path = output_dir / (name + ".stack")
    request_path = output_dir / (name + ".stack.request")
    stop = threading.Event()

    with stack_path.open("a", encoding="utf-8") as trace:
        last_request = None

        def watch_requests():
            nonlocal last_request
            while not stop.wait(0.05):
                try:
                    request = request_path.read_text(encoding="ascii")
                except FileNotFoundError:
                    continue
                if request == last_request:
                    continue
                last_request = request
                faulthandler.dump_traceback(file=trace, all_threads=True)
                trace.flush()

        watcher = threading.Thread(
            target=watch_requests,
            name=name + "-stack-probe",
            daemon=True,
        )
        watcher.start()
        try:
            yield
        finally:
            stop.set()
            watcher.join(timeout=0.2)
