import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import ExitStack, contextmanager
from pathlib import Path

import pytest
from playwright.sync_api import Page


ROOT_DIR = Path(__file__).resolve().parents[1]
EXAMPLES_APP = ROOT_DIR / "examples" / "app.py"


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_streamlit(port, process, *, base_url_path=""):
    deadline = time.time() + 20
    last_error = None
    base_url_path = base_url_path.strip("/")
    health_path = (
        f"/{base_url_path}/_stcore/health" if base_url_path else "/_stcore/health"
    )
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Streamlit exited while starting on port {port} "
                f"with code {process.returncode}"
            )
        try:
            with urllib.request.urlopen(
                f"http://localhost:{port}{health_path}",
                timeout=1,
            ) as response:
                if response.status == 200:
                    return
        except Exception as error:  # noqa: PERF203
            last_error = error
            time.sleep(0.25)
    raise RuntimeError(f"Streamlit did not start on port {port}: {last_error}")


def start_streamlit(app_path, port, cwd, *, base_url_path=""):
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--server.fileWatcherType",
        "none",
    ]
    if base_url_path:
        command.append(f"--server.baseUrlPath=/{base_url_path.strip('/')}")
    return subprocess.Popen(command, cwd=cwd)


def stop_process(process):
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@contextmanager
def streamlit_server(app_path, *, cwd=ROOT_DIR, base_url_path=""):
    last_error = None
    for _ in range(3):
        port = get_free_port()
        process = start_streamlit(
            app_path,
            port,
            cwd,
            base_url_path=base_url_path,
        )
        try:
            wait_for_streamlit(port, process, base_url_path=base_url_path)
        except RuntimeError as error:
            last_error = error
            stop_process(process)
            continue
        try:
            yield port
        finally:
            stop_process(process)
        return
    raise RuntimeError(f"Streamlit failed to start after 3 attempts: {last_error}")


@pytest.fixture(autouse=True, scope="session")
def run_streamlit():
    with streamlit_server(EXAMPLES_APP) as port:
        yield port


@pytest.fixture
def serve_streamlit():
    with ExitStack() as stack:
        yield lambda path: stack.enter_context(streamlit_server(path))


@pytest.fixture
def serve_streamlit_at_base_path():
    with ExitStack() as stack:
        yield lambda path, base_url_path: stack.enter_context(
            streamlit_server(path, base_url_path=base_url_path)
        )


@pytest.fixture
def http_page(playwright):
    """Exercise a real insecure origin without changing DNS or browser security."""
    browser = playwright.chromium.launch(
        args=[
            "--host-resolver-rules=MAP workbench.test 127.0.0.1",
            "--no-proxy-server",
        ]
    )
    try:
        yield browser.new_page(viewport={"width": 1440, "height": 1000})
    finally:
        browser.close()


@pytest.fixture(autouse=True, scope="function")
def goto_streamlit(request, run_streamlit):
    if "page" in request.fixturenames:
        page: Page = request.getfixturevalue("page")
        module_name = request.node.module.__name__
        home_test = (
            module_name.startswith("test_tutorial") or module_name == "test_smoke"
        )
        # Existing feature regressions start inside the lab, whose navigation
        # is separate from the new tutorial home. Tutorial tests exercise both.
        route = "" if home_test else "/node_style"
        page.goto(f"http://localhost:{run_streamlit}{route}")
