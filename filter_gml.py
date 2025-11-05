#!/usr/bin/env python3
import zipfile
import tempfile
import re
from pathlib import Path

UNLINK_NON_GML = True

def filter_file_by_ids(file_path, id_set):
    """Filter a single GML file to only include cityObjectMembers with IDs in id_set."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    result_lines = []
    inside_member = False
    current_member_lines = []
    keep_current_member = False
    matched_ids = set()

    for line in lines:
        if '<core:cityObjectMember>' in line or '<cityObjectMember>' in line:
            inside_member = True
            current_member_lines = [line]
            keep_current_member = False
            continue

        if '</core:cityObjectMember>' in line or '</cityObjectMember>' in line:
            current_member_lines.append(line)
            if keep_current_member:
                result_lines.extend(current_member_lines)
            inside_member = False
            current_member_lines = []
            keep_current_member = False
            continue

        if inside_member:
            current_member_lines.append(line)
            if not keep_current_member and 'gml:id="' in line:
                # Extract gml:id from line and check if it's in our set - O(1) lookup
                match = re.search(r'gml:id="([^"]+)"', line)
                if match and match.group(1) in id_set:
                    keep_current_member = True
                    matched_ids.add(match.group(1))
        else:
            result_lines.append(line)

    return ''.join(result_lines), matched_ids


def filter_gml_objects(src_zip, dst_zip, filter_dict):
    """
    Filter GML objects based on filter_dict.
    filter_dict format: {"path/to/file.gml": ["id1", "id2"], "other/path.gml": "all"}
    Use "all" to include all objects from a file without filtering.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        extract_path = temp_path / "extracted"
        extract_path.mkdir()

        print("extracting", src_zip, "to", extract_path)
        with zipfile.ZipFile(src_zip, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        udx_path = extract_path / "udx"
        all_matched_ids = []

        # Process each file in filter_dict independently
        for rel_path, ids in filter_dict.items():
            file_path = udx_path / rel_path

            if not file_path.exists() or not file_path.is_file():
                print(f"Warning: {rel_path} not found, skipping")
                continue

            if ids == "all":
                # Keep entire file as-is, no processing needed
                print(f"keeping all objects in {rel_path}")
                all_matched_ids.append(f"{rel_path}:all")
            else:
                # Filter this specific file by its ID set
                id_set = set(ids)
                print(f"filtering {rel_path} for {len(id_set)} IDs")
                modified_content, matched_ids = filter_file_by_ids(file_path, id_set)

                if matched_ids:
                    print(f"  found {len(matched_ids)} matching IDs in {rel_path}")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    all_matched_ids.extend(matched_ids)
                else:
                    print(f"  no matching IDs found in {rel_path}, removing file")
                    file_path.unlink()

        # Remove all files NOT in filter_dict
        for file in udx_path.glob("**/*"):
            if not file.is_file():
                continue
            rel_path = str(file.relative_to(udx_path))
            if rel_path not in filter_dict:
                if file.suffix.lower() == '.gml' or UNLINK_NON_GML:
                    file.unlink()

        if not all_matched_ids:
            raise ValueError(f"No GML objects matched filter")

        print("writing to", dst_zip)
        Path(dst_zip).parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dst_zip, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for file_path in extract_path.rglob('*'):
                if file_path.is_file():
                    zip_ref.write(file_path, file_path.relative_to(extract_path))