"""Start the private T3 backend and submit exactly one turn on it."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def private_port(server, runtime):
    deadline = time.monotonic() + 30
    while server.poll() is None and time.monotonic() < deadline:
        try:
            port = json.loads(runtime.read_text())["port"]
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.05)
            continue
        if type(port) is int and 0 < port < 65536:
            return port
        sys.exit("invalid private T3 server address")
    sys.exit("private T3 server failed to start")


def main():
    server_bin, client, *model = sys.argv[1:]
    data = Path(os.environ["T3CODE_HOME"])
    location = ["--base-dir", str(data)]
    prompt = sys.stdin.read()
    issued = subprocess.run([server_bin, "auth", "session", "issue", *location, "--token-only"],
                            stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if issued.returncode or not issued.stdout.strip():
        sys.exit("could not issue a token for the private T3 server")

    # Server output can include pairing secrets. Only the thread client writes
    # to the benchmark transcript. The outer guard owns both process trees.
    server = subprocess.Popen([server_bin, *location, "--host", "127.0.0.1", "--no-browser",
                               "--auto-bootstrap-project-from-cwd", str(Path.cwd())],
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port = private_port(server, data / "userdata/server-runtime.json")
        # The only configured destination is this attempt's loopback listener.
        config = data / "client.json"
        config.write_text(json.dumps({"servers": {"benchmark": {
            "httpUrl": f"http://127.0.0.1:{port}", "bearerTokenEnv": "T3_ATTEMPT_TOKEN",
        }}}))
        return subprocess.run(
            [client, "--config", str(config), "--server", "benchmark", "new", "--cwd", str(Path.cwd()),
             "--json", "--runtime-mode", "auto-accept-edits", *model, "--", prompt],
            stdin=subprocess.DEVNULL, env={**os.environ, "T3_ATTEMPT_TOKEN": issued.stdout.strip()},
        ).returncode
    finally:
        server.terminate()
        try:
            server.wait(timeout=2)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


if __name__ == "__main__":
    sys.exit(main())
