"""
Generic sandbox runner for non-Python operations.

Executes shell commands and other high-risk operations inside the configured
sandbox backend (docker/k8s) using the same configuration as code execution.
This keeps high-risk operations out of the main app container.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Literal

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox
from mcp_server_langgraph.execution.resource_limits import ResourceLimits
from mcp_server_langgraph.execution.sandbox import ExecutionResult, SandboxError

SandboxBackend = Literal["docker-engine", "kubernetes"]


@dataclass
class SandboxRunResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    timed_out: bool
    error_message: str | None = None


class SandboxRunner:
    """Execute commands inside the configured sandbox backend."""

    def __init__(self) -> None:
        self.backend: SandboxBackend = settings.code_execution_backend  # type: ignore[assignment]
        self.limits = ResourceLimits(
            timeout_seconds=settings.code_execution_timeout,
            memory_limit_mb=settings.code_execution_memory_limit_mb,
            cpu_quota=settings.code_execution_cpu_quota,
            disk_quota_mb=settings.code_execution_disk_quota_mb,
            max_processes=settings.code_execution_max_processes,
            network_mode=settings.code_execution_network_mode,  # type: ignore[arg-type]
            allowed_domains=tuple(settings.code_execution_allowed_domains),
        )

    def _docker_sandbox(self) -> DockerSandbox:
        return DockerSandbox(
            limits=self.limits,
            image=settings.code_execution_docker_image,
            socket_path=settings.code_execution_docker_socket,
        )

    def run_bash(self, command: str, timeout_override: int | None = None) -> SandboxRunResult:
        """Run a bash command inside the sandbox."""
        timeout = timeout_override or self.limits.timeout_seconds
        start = time.perf_counter()

        if self.backend == "docker-engine":
            sandbox = self._docker_sandbox()
            # Use /bin/bash -lc to allow basic shell features (within allowlist enforced by caller)
            wrapped_command = f"bash -lc {repr(command)}"
            result: ExecutionResult = sandbox.execute(wrapped_command, is_shell_command=True, timeout_seconds=timeout)
        else:
            raise SandboxError(f"Sandbox backend {self.backend} not implemented for bash commands")

        duration_ms = (time.perf_counter() - start) * 1000.0
        return SandboxRunResult(
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.exit_code if result.exit_code is not None else 1,
            duration_ms=duration_ms,
            timed_out=result.timed_out,
            error_message=result.error_message,
        )

    def run_web_fetch(
        self,
        url: str,
        timeout_override: int | None = None,
        max_bytes: int | None = None,
    ) -> SandboxRunResult:
        """Fetch a URL inside the sandbox using Python stdlib (no external deps)."""
        timeout = timeout_override or self.limits.timeout_seconds
        max_size = max_bytes or 10 * 1024 * 1024
        script = f"""
import json, sys, urllib.request
url = {url!r}
timeout = {timeout}
max_bytes = {max_size}
try:
    req = urllib.request.Request(url, headers={{"User-Agent": "sandbox-web-fetch"}})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get("Content-Type", "") if resp.headers else ""
        status = getattr(resp, "status", None) or resp.getcode()
        data = resp.read(max_bytes + 1)
        truncated = len(data) > max_bytes
        if truncated:
            data = data[:max_bytes]
        text = data.decode("utf-8", errors="replace")
        json.dump({{"status": status, "content_type": content_type, "text": text, "truncated": truncated}}, sys.stdout)
except Exception as e:
    sys.stderr.write(str(e))
    sys.exit(1)
"""
        return self._run_python_script(script, timeout_override=timeout)

    def run_write_file(self, file_path: str, content: str, create_directories: bool = True) -> SandboxRunResult:
        """Write a file inside the sandbox (isolated FS)."""
        script = f"""
from pathlib import Path
import sys
path = Path({file_path!r})
create_dirs = {create_directories!r}
if not create_dirs and not path.parent.exists():
    sys.stderr.write("Parent directory does not exist")
    sys.exit(1)
if create_dirs:
    path.parent.mkdir(parents=True, exist_ok=True)
path.write_text({content!r}, encoding='utf-8')
print("Wrote", path)
"""
        return self._run_python_script(script)

    def run_edit_file(self, file_path: str, old_string: str, new_string: str, replace_all: bool) -> SandboxRunResult:
        """Edit a file inside the sandbox (isolated FS)."""
        script = f"""
from pathlib import Path
path = Path({file_path!r})
text = path.read_text(encoding='utf-8')
old = {old_string!r}
new = {new_string!r}
count = text.count(old)
if count == 0:
    print("No occurrences found")
    raise SystemExit(1)
if {replace_all!r}:
    text = text.replace(old, new)
else:
    text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print(f"Replaced {{'all' if {replace_all!r} else 'first'}} occurrence(s), total matches: {{count}}")
"""
        return self._run_python_script(script)

    def run_screenshot(self, payload: dict) -> SandboxRunResult:
        """Run screenshot/PDF captures in the sandbox using Playwright."""
        script = f"""
import base64, json, sys
from playwright.sync_api import sync_playwright

payload = {json.dumps(payload)}
operation = payload.get("operation")
url = payload.get("url")

def fail(msg):
    json.dump({{"error": msg}}, sys.stdout)
    sys.exit(1)

if not url:
    fail("url is required")

timeout = int(payload.get("timeout", 30000))
viewport_width = int(payload.get("viewport_width", 1280))
viewport_height = int(payload.get("viewport_height", 720))

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--user-data-dir=/tmp/chrome-data", "--disable-dev-shm-usage"],
    )
    page = browser.new_page(viewport={{"width": viewport_width, "height": viewport_height}})

    try:
        page.goto(url, timeout=timeout)
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception as e:
        fail(f"Navigation failed: {{e}}")

    if operation == "capture_screenshot":
        image_bytes = page.screenshot(full_page=bool(payload.get("full_page", False)))
        output = {{
            "image_data": base64.b64encode(image_bytes).decode("utf-8"),
            "mime_type": "image/png",
            "url": url,
            "title": page.title(),
            "width": viewport_width,
            "height": viewport_height,
        }}
    elif operation == "capture_element_screenshot":
        selector = payload.get("selector")
        if not selector:
            fail("selector is required for element screenshot")
        element = page.locator(selector)
        image_bytes = element.screenshot()
        output = {{
            "image_data": base64.b64encode(image_bytes).decode("utf-8"),
            "mime_type": "image/png",
            "url": url,
            "selector": selector,
            "title": page.title(),
        }}
    elif operation == "capture_pdf":
        pdf_bytes = page.pdf(
            format=payload.get("format") or "A4",
            print_background=bool(payload.get("print_background", True)),
        )
        output = {{
            "pdf_data": base64.b64encode(pdf_bytes).decode("utf-8"),
            "mime_type": "application/pdf",
            "url": url,
            "title": page.title(),
        }}
    elif operation == "wait_and_capture":
        wait_for = payload.get("wait_for")
        if not wait_for:
            fail("wait_for selector is required for wait_and_capture")
        try:
            page.wait_for_selector(wait_for, timeout=timeout)
        except Exception as e:
            fail(f"Wait failed: {{e}}")
        image_bytes = page.screenshot()
        output = {{
            "image_data": base64.b64encode(image_bytes).decode("utf-8"),
            "mime_type": "image/png",
            "url": url,
            "title": page.title(),
            "waited_for": wait_for,
            "width": viewport_width,
            "height": viewport_height,
        }}
    else:
        fail("unsupported screenshot operation")

    json.dump(output, sys.stdout)
"""
        return self._run_python_script(script, timeout_override=self.limits.timeout_seconds)

    def run_computer_use(self, action: str, payload: dict | None = None) -> SandboxRunResult:
        """Run computer-use actions inside the sandbox using Playwright."""
        payload = payload or {}
        payload["action"] = action
        script = f"""
import json, sys
from playwright.sync_api import sync_playwright

payload = {json.dumps(payload)}
action = payload.get("action")
timeout = int(payload.get("timeout", 30000))
url = payload.get("url")

def success(**kwargs):
    json.dump({{"success": True, "action": action, **kwargs}}, sys.stdout)
    sys.exit(0)

def failure(msg):
    json.dump({{"success": False, "action": action, "error": msg}}, sys.stdout)
    sys.exit(1)

if action == "get_screen_info":
    success(width=1920, height=1080, device_pixel_ratio=1.0, color_depth=24)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--user-data-dir=/tmp/chrome-data", "--disable-dev-shm-usage"],
    )
    page = browser.new_page()
    if url:
        try:
            resp = page.goto(url, timeout=timeout)
            status = resp.status if resp else None
            page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            failure(f"Navigation failed: {{e}}")
    else:
        status = None

    if action == "navigate":
        if not url:
            failure("url is required for navigate")
        success(url=url, status=status or 200)
    elif action == "mouse_click":
        try:
            selector = payload.get("selector")
            button = payload.get("button", "left")
            click_count = int(payload.get("click_count", 1))
            if selector:
                page.click(selector, button=button, click_count=click_count, timeout=timeout)
                success(selector=selector, button=button, click_count=click_count)
            else:
                x = int(payload.get("x", 0))
                y = int(payload.get("y", 0))
                page.mouse.click(x, y, button=button, click_count=click_count)
                success(coordinates={{"x": x, "y": y}}, button=button, click_count=click_count)
        except Exception as e:
            failure(f"mouse_click failed: {{e}}")
    elif action == "mouse_move":
        try:
            x = int(payload.get("x", 0))
            y = int(payload.get("y", 0))
            page.mouse.move(x, y)
            success(coordinates={{"x": x, "y": y}})
        except Exception as e:
            failure(f"mouse_move failed: {{e}}")
    elif action == "mouse_drag":
        try:
            start_x = int(payload.get("start_x", 0))
            start_y = int(payload.get("start_y", 0))
            end_x = int(payload.get("end_x", 0))
            end_y = int(payload.get("end_y", 0))
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(end_x, end_y)
            page.mouse.up()
            success(start={{"x": start_x, "y": start_y}}, end={{"x": end_x, "y": end_y}})
        except Exception as e:
            failure(f"mouse_drag failed: {{e}}")
    elif action == "keyboard_type":
        try:
            selector = payload.get("selector")
            text = payload.get("text", "")
            if selector:
                page.click(selector, timeout=timeout)
            page.keyboard.type(text)
            success(text_typed=text, selector=selector)
        except Exception as e:
            failure(f"keyboard_type failed: {{e}}")
    elif action == "keyboard_press":
        key = payload.get("key")
        modifiers = payload.get("modifiers") or []
        if not key:
            failure("key is required for keyboard_press")
        try:
            combo = "+".join(modifiers + [key]) if modifiers else key
            page.keyboard.press(combo)
            success(key_pressed=key, modifiers=modifiers)
        except Exception as e:
            failure(f"keyboard_press failed: {{e}}")
    elif action == "scroll":
        direction = payload.get("direction")
        amount = int(payload.get("amount", 100))
        selector = payload.get("selector")
        try:
            if selector:
                page.locator(selector).scroll_into_view_if_needed(timeout=timeout)
                success(action="scroll_into_view", selector=selector)
            elif direction:
                if direction in ("up", "down"):
                    delta = amount if direction == "down" else -amount
                    page.mouse.wheel(0, delta)
                elif direction in ("left", "right"):
                    delta = amount if direction == "right" else -amount
                    page.mouse.wheel(delta, 0)
                success(action="scroll", direction=direction, amount=amount)
            else:
                failure("direction or selector required for scroll")
        except Exception as e:
            failure(f"scroll failed: {{e}}")
    elif action == "get_element_info":
        selector = payload.get("selector")
        if not selector:
            failure("selector is required for get_element_info")
        try:
            element = page.locator(selector)
            box = element.bounding_box() or {{}}
            success(
                selector=selector,
                bounds={{k: box.get(k) for k in ("x", "y", "width", "height") if box.get(k) is not None}},
                visible=bool(element.is_visible()),
                tag_name=element.evaluate("el => el.tagName") if element.count() else None,
                text_content=element.text_content(),
            )
        except Exception as e:
            failure(f"get_element_info failed: {{e}}")
    elif action == "go_back":
        try:
            resp = page.go_back()
            success(status=resp.status if resp else None)
        except Exception as e:
            failure(f"go_back failed: {{e}}")
    elif action == "go_forward":
        try:
            resp = page.go_forward()
            success(status=resp.status if resp else None)
        except Exception as e:
            failure(f"go_forward failed: {{e}}")
    elif action == "fill_form":
        try:
            fields = payload.get("fields") or {{}}
            for selector, value in fields.items():
                page.fill(selector, value, timeout=timeout)
            success(fields_filled=len(fields), fields=list(fields.keys()))
        except Exception as e:
            failure(f"fill_form failed: {{e}}")
    elif action == "select_option":
        selector = payload.get("selector")
        if not selector:
            failure("selector is required for select_option")
        value = payload.get("value")
        label = payload.get("label")
        index = payload.get("index")
        try:
            element = page.locator(selector)
            if value is not None:
                element.select_option(value=value)
            elif label is not None:
                element.select_option(label=label)
            elif index is not None:
                element.select_option(index=int(index))
            else:
                failure("value, label, or index required for select_option")
            success(selector=selector, value=value, label=label, index=index)
        except Exception as e:
            failure(f"select_option failed: {{e}}")
    else:
        failure(f"Unsupported action: {{action}}")
"""
        return self._run_python_script(script, timeout_override=self.limits.timeout_seconds)

    def _run_python_script(self, script: str, timeout_override: int | None = None) -> SandboxRunResult:
        """Helper to run a Python snippet inside the sandbox."""
        start = time.perf_counter()
        if self.backend == "docker-engine":
            sandbox = self._docker_sandbox()
            result = sandbox.execute(script, is_shell_command=False, timeout_seconds=timeout_override)
        else:
            raise SandboxError(f"Sandbox backend {self.backend} not implemented for python scripts")

        duration_ms = (time.perf_counter() - start) * 1000.0
        return SandboxRunResult(
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.exit_code if result.exit_code is not None else 1,
            duration_ms=duration_ms,
            timed_out=result.timed_out,
            error_message=result.error_message,
        )


def get_sandbox_runner() -> SandboxRunner:
    return SandboxRunner()
