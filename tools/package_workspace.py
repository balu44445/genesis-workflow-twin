"""Bundle reviewed source and a built wheel, excluding private runtime evidence/secrets."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
paths = [root / name for name in ("README.md", "pyproject.toml", "requirements.lock", ".gitignore",
                                    ".dockerignore", "Dockerfile", "render.yaml")]
for pattern in ("genesis/*.py", "genesis/static/*", "servicenow/*.js", "examples/*.json",
                "docs/*.md", "tests/*.py", "scripts/*.py", "scripts/*.cjs", "tools/*.py"):
    paths.extend(sorted(root.glob(pattern)))
wheel = root / "dist/genesis_workflow_twin-0.2.0-py3-none-any.whl"
assert wheel.is_file(), "Build the 0.2 wheel before packaging"
paths.append(wheel)
assert len(paths) == len(set(paths))
metadata = {"release": "0.2.0", "mode": "local_workspace_public_demo_package_and_uninstalled_servicenow_upgrade",
            "external_ai": "disabled by default; mock-tested only",
            "target_pdi_installation": "pending second instance",
            "live_guard_concurrency": "not tested",
            "previous_live_pdi_xml": "separate historical 0.1 package, not included",
            "files": {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
destination = root / "dist/GENESIS-Workspace-0.2.zip"
with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in paths:
        archive.write(path, "GENESIS-Workspace-0.2/" + path.relative_to(root).as_posix())
    archive.writestr("GENESIS-Workspace-0.2/RELEASE_MANIFEST.json", json.dumps(metadata, indent=2) + "\n")
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
    assert not any("pdi-local/" in name or "__pycache__" in name or name.endswith(".env") for name in archive.namelist())
    for path, expected in metadata["files"].items():
        assert hashlib.sha256(archive.read("GENESIS-Workspace-0.2/" + path)).hexdigest() == expected
print(json.dumps({"package": str(destination), "files": len(paths),
                  "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}, indent=2))
