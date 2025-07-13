#!/usr/bin/env python3
import sys, pathlib, json
from ingest.ingest_pack import process_doc
from ingest.override_utils import load_manifest, extract_all_overrides, make_pack_overview


pack, version = sys.argv[1], sys.argv[2]
root = pathlib.Path("data/raw_docs") / pack / version
manifest = load_manifest(root / "manifest.json")

# 1. Ingest overview
overview_text = make_pack_overview({"name": pack, "version": version, "files": manifest}, [])
process_doc(
    content=overview_text,
    metadata={"doc_type": "pack_overview", "pack_id": pack, "pack_version": version}
)

# 2. Ingest overrides
overrides = extract_all_overrides(root / "overrides", pack, version)
for meta, delta in overrides:
    process_doc(content=json.dumps(delta), metadata=meta)

# 3. (Optional) Ingest base-mod docs if present
for md in (root/"mods").glob("*.md"):
    mod_id, mod_ver = md.stem.split("-",1)
    process_doc(md, metadata={
        "doc_type":"base_mod","mod_id":mod_id,"mod_version":mod_ver
    })

print("Pack ingestion queued.")
