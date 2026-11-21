"""Builds the Lambda package: handler code + dependencies for Linux x86_64 / Python 3.12.

Called by Terraform (data "external"), so stdout must contain only the JSON result.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

query = json.load(sys.stdin)
src = Path(query["src"]).resolve()
out = Path(query["out"]).resolve()
requirements = src / "requirements.txt"

req_hash = hashlib.sha256(requirements.read_bytes()).hexdigest()
stamp = out / ".requirements.sha256"

# Reinstall dependencies only when requirements.txt changes
if not stamp.exists() or stamp.read_text() != req_hash:
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--quiet",
            "--target", str(out),
            "--platform", "manylinux2014_x86_64",
            "--implementation", "cp",
            "--python-version", "3.12",
            "--only-binary=:all:",
            "-r", str(requirements),
        ],
        check=True,
        stdout=sys.stderr,
    )
    stamp.write_text(req_hash)

for py_file in src.glob("*.py"):
    shutil.copy2(py_file, out / py_file.name)

print(json.dumps({"dir": out.as_posix()}))
