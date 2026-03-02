import asyncio
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import AsyncIterator, Callable

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Safety: prevent injection in terraform commands ─────────────
_SAFE_WORKSPACE_PATTERN = re.compile(r"^[a-zA-Z0-9_\-/\\:.]+$")


def _find_terraform_binary() -> str:
    """
    Locate the terraform binary on the system.

    Checks, in order:
    1. Standard PATH lookup via shutil.which()
    2. Refreshed PATH from the Windows registry (Machine + User)
    3. Common install locations on Windows
    """
    # 1) Check current PATH
    found = shutil.which("terraform")
    if found:
        print(f"[TF] terraform found in PATH: {found}")
        return found

    # 2) On Windows, refresh PATH from registry and try again
    if os.name == "nt":
        try:
            machine_path = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 '[System.Environment]::GetEnvironmentVariable("Path","Machine")'],
                text=True, timeout=5,
            ).strip()
            user_path = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 '[System.Environment]::GetEnvironmentVariable("Path","User")'],
                text=True, timeout=5,
            ).strip()
            combined = f"{machine_path};{user_path}"
            found = shutil.which("terraform", path=combined)
            if found:
                print(f"[TF] terraform found via refreshed system PATH: {found}")
                return found
        except Exception as e:
            print(f"[TF] WARNING: Failed to refresh PATH from registry: {e}")

        # 3) Common Windows install directories
        common_dirs = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
            Path(os.environ.get("ProgramFiles", "")) / "Terraform",
            Path(os.environ.get("USERPROFILE", "")) / "scoop" / "shims",
        ]
        for d in common_dirs:
            candidate = d / "terraform.exe"
            if candidate.exists():
                print(f"[TF] terraform found at common path: {candidate}")
                return str(candidate)

    print("[TF] ERROR: terraform NOT FOUND anywhere on the system")
    return "terraform"  # fall through — will fail with a clear error


def _get_refreshed_env() -> dict[str, str]:
    """Build environment dict with refreshed PATH and AWS credentials."""
    env = os.environ.copy()

    # Refresh PATH from Windows registry so terraform is always found
    if os.name == "nt":
        try:
            machine_path = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 '[System.Environment]::GetEnvironmentVariable("Path","Machine")'],
                text=True, timeout=5,
            ).strip()
            user_path = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 '[System.Environment]::GetEnvironmentVariable("Path","User")'],
                text=True, timeout=5,
            ).strip()
            env["PATH"] = f"{machine_path};{user_path}"
        except Exception as e:
            print(f"[TF] WARNING: Could not refresh PATH: {e}")

    # Inject AWS credentials
    if settings.AWS_ACCESS_KEY_ID:
        env["AWS_ACCESS_KEY_ID"] = settings.AWS_ACCESS_KEY_ID
    if settings.AWS_SECRET_ACCESS_KEY:
        env["AWS_SECRET_ACCESS_KEY"] = settings.AWS_SECRET_ACCESS_KEY
    if settings.AWS_DEFAULT_REGION:
        env["AWS_DEFAULT_REGION"] = settings.AWS_DEFAULT_REGION
    return env


class TerraformExecutor:
    """
    Executes Terraform CLI commands (init, plan, apply, destroy)
    in isolated project workspace directories.

    Uses subprocess.run in a thread (via asyncio.to_thread) for
    Windows compatibility — asyncio.create_subprocess_exec does NOT
    work on Windows with Python 3.14.
    """

    def __init__(self, terraform_binary: str | None = None) -> None:
        self.terraform_binary = terraform_binary or _find_terraform_binary()
        print(f"[TF] TerraformExecutor using binary: {self.terraform_binary}")

    async def init(self, workspace_dir: Path) -> tuple[int, str]:
        """Run `terraform init` in the workspace."""
        return await self._run_command(["init", "-no-color"], workspace_dir)

    async def plan(self, workspace_dir: Path) -> tuple[int, str]:
        """Run `terraform plan` in the workspace."""
        return await self._run_command(
            ["plan", "-no-color", "-input=false"], workspace_dir
        )

    async def apply(self, workspace_dir: Path) -> tuple[int, str]:
        """Run `terraform apply -auto-approve` in the workspace."""
        return await self._run_command(
            ["apply", "-auto-approve", "-no-color", "-input=false"], workspace_dir
        )

    async def destroy(self, workspace_dir: Path) -> tuple[int, str]:
        """Run `terraform destroy -auto-approve` in the workspace."""
        return await self._run_command(
            ["destroy", "-auto-approve", "-no-color", "-input=false"], workspace_dir
        )

    async def destroy_target(self, workspace_dir: Path, resource_address: str) -> tuple[int, str]:
        """
        Run `terraform destroy -target=<resource_address>` for a single resource.

        Args:
            workspace_dir: Path to the Terraform workspace.
            resource_address: Fully-qualified resource address, e.g.
                              'aws_ecs_service.main' or 'aws_s3_bucket.content_bucket'.
        Returns:
            (return_code, combined_output)
        """
        # Validate resource address — allow all valid Terraform state address characters.
        # Terraform addresses look like: aws_ecs_service.my-service, module.vpc.aws_vpc.main,
        # aws_subnet.private[0].  Shell injection is not possible since args are passed as
        # a list to subprocess (not via shell=True), but we still guard against nonsense.
        ALLOWED = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-[]{}()')
        if not resource_address or not all(c in ALLOWED for c in resource_address):
            bad_chars = [c for c in resource_address if c not in ALLOWED]
            raise ValueError(
                f"Invalid resource address {resource_address!r}. "
                f"Disallowed characters: {bad_chars}"
            )
        return await self._run_command(
            ["destroy", f"-target={resource_address}", "-auto-approve", "-no-color", "-input=false"],
            workspace_dir,
        )

    async def state_list(self, workspace_dir: Path) -> tuple[int, str]:
        """Run `terraform state list` to get all resources from the state file."""
        return await self._run_command(["state", "list", "-no-color"], workspace_dir)

    async def execute_stream(
        self,
        args: list[str],
        workspace_dir: Path,
    ) -> AsyncIterator[str]:
        """
        Execute a terraform command and yield stdout/stderr line by line.
        Uses a background thread and asyncio.Queue for Windows compatibility.
        Lines are yielded in real-time as the process produces them.
        """
        cmd = [self.terraform_binary] + args
        env = _get_refreshed_env()
        workspace_str = str(workspace_dir.resolve())

        logger.info(f"Streaming CMD: {' '.join(cmd)} in {workspace_str}")

        queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _read_stream():
            """Read process output in a background thread, pushing lines to the queue."""
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=workspace_str,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,  # Line buffered
                    encoding="utf-8",
                    errors="replace",
                )
                # Read line-by-line and push to queue
                for line in iter(proc.stdout.readline, ""):
                    if line:
                        asyncio.run_coroutine_threadsafe(queue.put(line), loop)
                    else:
                        break
                proc.stdout.close()
                return_code = proc.wait()
                if return_code != 0:
                    asyncio.run_coroutine_threadsafe(
                        queue.put(f"\n[ERROR] Command failed with exit code {return_code}\n"),
                        loop,
                    )
            except Exception as e:
                logger.error(f"Stream reader error: {e}")
                asyncio.run_coroutine_threadsafe(
                    queue.put(f"\n[ERROR] Stream reader exception: {e}\n"), loop
                )
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        # Launch reader in background thread (non-blocking!)
        reader_future = loop.run_in_executor(None, _read_stream)

        # Yield lines as they arrive from the background thread
        while True:
            line = await queue.get()
            if line is None:
                break
            yield line

        # Ensure the reader thread is finished
        await reader_future

    def _run_sync(self, cmd: list[str], cwd: str, env: dict[str, str]) -> tuple[int, str]:
        """
        Run terraform synchronously via subprocess.run.
        This runs in a thread via asyncio.to_thread.
        """
        print(f"[TF] subprocess.run: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,  # 5 minute timeout
        )
        combined = result.stdout
        if result.stderr:
            combined += "\n" + result.stderr
        return result.returncode, combined.strip()

    async def _run_command(
        self,
        args: list[str],
        workspace_dir: Path,
    ) -> tuple[int, str]:
        """
        Execute a terraform command via subprocess.run in a thread.

        Returns:
            Tuple of (return_code, combined_output).
        """
        # Validate workspace path
        workspace_str = str(workspace_dir.resolve())
        if not _SAFE_WORKSPACE_PATTERN.match(workspace_str):
            raise ValueError(f"Invalid workspace path: {workspace_str}")

        if not workspace_dir.exists():
            raise FileNotFoundError(f"Workspace not found: {workspace_dir}")

        cmd = [self.terraform_binary] + args
        print(f"[TF] ▶ CMD: {' '.join(cmd)}")
        print(f"[TF]   CWD: {workspace_dir}")
        print(f"[TF]   Files: {[f.name for f in workspace_dir.iterdir() if f.is_file()]}")

        env = _get_refreshed_env()

        # Run in a thread so we don't block the event loop
        return_code, output = await asyncio.to_thread(
            self._run_sync, cmd, str(workspace_dir), env
        )

        print(f"[TF] ◀ EXIT: {return_code}  OUTPUT_LEN: {len(output)}")
        if output:
            for line in output.split('\n')[:25]:
                print(f"[TF]   | {line}")
            if output.count('\n') > 25:
                print(f"[TF]   | ... ({output.count(chr(10)) - 25} more lines)")

        if return_code != 0:
            print(f"[TF] ⚠ FAILED with exit code {return_code}")

        return return_code, output
