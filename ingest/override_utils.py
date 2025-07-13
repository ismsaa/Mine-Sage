import json
import os
import pathlib

def load_manifest(manifest_path: str) -> list[dict]:
    """
    Load the modpack manifest.json and return a list of mod entries.

    Each entry is a dict from the manifest's "files" array, containing metadata
    like projectID and fileID. Adjust keys based on the actual manifest schema.
    """
    path = pathlib.Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")
    with open(path, 'r', encoding='utf-8') as f:
        mf = json.load(f)
    return mf.get("files", [])


def extract_all_overrides(overrides_root: str, pack_id: str, pack_version: str) -> list[tuple[dict, dict]]:
    """
    Walk the overrides directory and parse deltas from subfolders.

    Returns a list of tuples (metadata, override_data) where:
      - metadata is a dict including pack_id, pack_version, category, etc.
      - override_data is the parsed JSON or dict of deltas for that category.
    """
    root = pathlib.Path(overrides_root)
    if not root.exists():
        raise FileNotFoundError(f"Overrides directory not found at {overrides_root}")
    results = []
    for sub in root.iterdir():
        if not sub.is_dir():
            continue
        # Read all files under this subcategory into one dict
        delta = {}
        for file in sub.rglob("*.json"):
            try:
                data = json.loads(open(file, 'r', encoding='utf-8').read())
            except json.JSONDecodeError:
                # If not JSON, store raw text
                data = open(file, 'r', encoding='utf-8').read()
            delta[file.name] = data
        if delta:
            meta = {
                "doc_type": "pack_override",
                "pack_id": pack_id,
                "pack_version": pack_version,
                "category": sub.name
            }
            results.append((meta, delta))
    return results


def make_pack_overview(manifest_entries: list[dict], overrides_summary: list[tuple[dict, dict]], pack_name: str, pack_version: str) -> str:
    """
    Generate a markdown overview text for the modpack.

    manifest_entries: list of entries from load_manifest
    overrides_summary: list of (meta, delta) tuples from extract_all_overrides
    pack_name: human-readable pack name
    pack_version: version string
    """
    lines = [f"# {pack_name} v{pack_version} Overview", ""]
    lines.append("## Included Mods:")
    for entry in manifest_entries:
        pid = entry.get("projectID")
        fid = entry.get("fileID")
        name = entry.get("projectSlug") or pid
        lines.append(f"- **{name}** (project ID: {pid}, file ID: {fid})")
    lines.append("")
    lines.append("## Override Categories:")
    for meta, delta in overrides_summary:
        cat = meta.get("category")
        count = len(delta)
        lines.append(f"- **{cat}**: {count} items changed")
    return "\n".join(lines)
