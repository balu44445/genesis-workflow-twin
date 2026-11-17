"""Review an exported GENESIS update set and build an explicitly scoped bundle."""
from pathlib import Path
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("export", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
out = root / "dist" / "genesis-pdi-demo"
out.mkdir(parents=True, exist_ok=True)
tree = ET.parse(args.export)
doc = tree.getroot()
allowed_types = {"Dictionary", "Script Include", "Form Layout", "Field Label",
                 "Access Control", "Access Roles", "Table", "Role",
                 "Scripted REST Resource", "Scripted REST API"}
scripts = {"GenesisCore": "GenesisCore.js", "GenesisGateway": "GenesisGateway.js",
           "Export model": "resource_get_model.js", "Create request": "resource_create_request.js",
           "Apply action": "resource_action.js"}
kept, excluded, checked = [], [], []
for entry in list(doc.findall("sys_update_xml")):
    name, typ, target = (entry.findtext(k) or "" for k in ("name", "type", "target_name"))
    item = {"name": name, "type": typ, "target": target}
    if typ not in allowed_types and not (typ == "System Property" and target == "u_genesis.manifest"):
        excluded.append(item)
        doc.remove(entry)
        continue
    payload = ET.fromstring(entry.findtext("payload"))
    if target in scripts:
        nodes = [e for e in payload.iter() if e.tag in ("script", "operation_script") and e.text]
        expected = (root / "servicenow" / scripts[target]).read_text().strip()
        assert any(e.text.strip() == expected for e in nodes), f"Script mismatch: {target}"
        checked.append(target)
    if typ == "Scripted REST Resource":
        for flag in ("active", "requires_authentication", "requires_acl_authorization"):
            assert payload.findtext(".//" + flag) == "true", (target, flag)
    if target == "u_genesis.manifest":
        manifest = json.loads(payload.findtext(".//value"))
        assert manifest["policy"]["require_distinct_approver"] is True
        assert manifest["revision"] == "demo-fixed-1"
        assert len(manifest["actors"]) == 3
    kept.append(item)
assert len(kept) == 37 and len(excluded) == 6, (len(kept), len(excluded))
assert set(checked) == set(scripts)
transport = out / "GENESIS_PDI_Demo_curated.xml"
tree.write(transport, encoding="utf-8", xml_declaration=True)
assert len(ET.parse(transport).getroot().findall("sys_update_xml")) == 37
audit = {"source_export_sha256": hashlib.sha256(args.export.read_bytes()).hexdigest(),
         "transport_sha256": hashlib.sha256(transport.read_bytes()).hexdigest(),
         "retained": kept, "excluded": excluded, "scripts_match_source": checked,
         "target_import_tested": False,
         "users_and_role_assignments_transported": False,
         "target_actor_ids_must_be_remapped": True}
(out / "EXPORT_AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n")
files = ["docs/PDI_PACKAGE_INSTALL.md", "docs/PDI_DEMO_RUNBOOK.md", "docs/PDI_LIVE_STATUS.md",
         "docs/PDI_SETUP.md", "examples/vulnerable.json", "examples/fixed.json"]
files += ["servicenow/" + f for f in scripts.values()]
for relative in files:
    src, dst = root / relative, out / relative
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
paths = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
(out / "SHA256SUMS.txt").write_text("".join(
    hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.relative_to(out).as_posix() + "\n" for p in paths))
archive = out.parent / "GENESIS-PDI-Demo.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(out.rglob("*")):
        if p.is_file():
            z.write(p, "genesis-pdi-demo/" + p.relative_to(out).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert all(not n.startswith("/") and ".." not in Path(n).parts for n in z.namelist())
print(json.dumps({"archive": str(archive), "retained": len(kept), "excluded": len(excluded),
                  "script_matches": len(checked), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}))
