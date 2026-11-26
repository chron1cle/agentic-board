"""Own one harness process tree until it exits or the benchmark's pipe closes."""

import ctypes
import os
import select
import shutil
import signal
import subprocess
import sys
from pathlib import Path


def stop_workers(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()

    # Linux reparents daemonized descendants to this subreaper. Killing one
    # generation can expose another, so drain until there are no children.
    children = Path(f"/proc/self/task/{os.getpid()}/children")
    if sys.platform.startswith("linux"):
        while pids := children.read_text().split():
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                    os.waitpid(int(pid), 0)
                except (ProcessLookupError, ChildProcessError):
                    pass


def main():
    lifeline = int(sys.argv[1])
    if sys.platform.startswith("linux"):
        pr_set_child_subreaper = 36
        if ctypes.CDLL(None, use_errno=True).prctl(pr_set_child_subreaper, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "could not supervise harness descendants")
    # Check before spawning as well as during execution. Only the engine owns
    # the write end, so EOF also covers SIGTERM, SIGKILL, and a runner crash.
    if select.select([lifeline], [], [], 0)[0]:
        return 124
    process = subprocess.Popen(sys.argv[3:], process_group=0)
    try:
        while process.poll() is None:
            if select.select([lifeline], [], [], 0.025)[0]:
                return 124
        return process.returncode if process.returncode >= 0 else 128 - process.returncode
    finally:
        stop_workers(process)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OSError as error:
        print(f"could not run supervised harness: {error}", file=sys.stderr)
        sys.exit(127)
    finally:
        # The owner may have been killed before its TemporaryDirectory cleanup.
        if sys.argv[2]:
            shutil.rmtree(sys.argv[2], ignore_errors=True)
