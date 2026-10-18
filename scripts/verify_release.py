# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: uv run python scripts/verify_release.py
"""Install and verify the actual source ZIP in an independent temporary directory."""

import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final
from zipfile import ZipFile

ROOT: Final = Path(__file__).resolve().parents[1]


def main() -> None:
    """A clean environment must not depend on this checkout's editable installation."""
    executable = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("TCM_")}
    environment.pop("VIRTUAL_ENV", None)
    environment["TCM_MODEL_MODE"] = "offline"
    transcript: list[str] = []
    with TemporaryDirectory(prefix="tcm-course-verify-") as temporary:
        with ZipFile(ROOT / "dist/tcm-agent-course-v1.zip") as archive:
            archive.extractall(temporary)
        cwd = Path(temporary) / "tcm-agent-course"
        commands = (
            ("sync", "--all-extras", "--frozen"),
            ("run", "tcm", "init-db"),
            ("run", "tcm", "run", "--text", "什么是四诊？"),
            ("run", "pytest", "-q"),
            ("run", "pytest", "exercises/acceptance.py", "-q"),
            ("run", "python", "-m", "labs.trace_demo"),
            ("run", "python", "-m", "labs.benchmark"),
            ("run", "python", "-m", "labs.run_all"),
            ("run", "python", "scripts/check_course.py"),
            ("run", "python", "scripts/clinical_knowledge.py", "audit"),
            ("run", "python", "scripts/clinical_knowledge.py", "build-index"),
            ("run", "python", "examples/clinical_mcp_client.py"),
        )
        for arguments in commands:
            result = subprocess.run(  # noqa: S603
                [executable, *arguments],
                cwd=cwd,
                env=environment,
                text=True,
                capture_output=True,
                check=True,
                timeout=180,
            )
            output = (result.stdout + result.stderr).replace(
                str(cwd), "<temporary-build-directory>"
            )
            transcript.append(
                "uv " + " ".join(arguments) + "\n" + output.replace(str(ROOT), "<project-root>")
            )
    (ROOT / "evidence/clean-install.txt").write_text("\n\n".join(transcript), encoding="utf-8")
    print("Source ZIP clean install and execution verified")


if __name__ == "__main__":
    main()
