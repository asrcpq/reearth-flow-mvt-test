#!/usr/bin/env python3
import zipfile
import re
from pathlib import Path

UNLINK_NON_GML = True

def filter_gml_content(content, id_set):
    lines = content.decode('utf-8').splitlines(keepends=True)
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
                match = re.search(r'gml:id="([^"]+)"', line)
                if match and match.group(1) in id_set:
                    keep_current_member = True
                    matched_ids.add(match.group(1))
        else:
            result_lines.append(line)

    return ''.join(result_lines).encode('utf-8'), matched_ids


def normalize_filter_paths(filter_dict):
    return {f"udx/{k}": v for k, v in filter_dict.items()}


def should_keep_unfiltered_file(rel_path):
    if not rel_path.startswith("udx/"):
        return True

    file_suffix = Path(rel_path).suffix.lower()
    if file_suffix == '.gml':
        return False

    return not UNLINK_NON_GML


def process_filtered_file(src_zip, item, ids):
    if ids == "all":
        print(f"keeping all objects in {item.filename}")
        return src_zip.read(item), [f"{item.filename}:all"]

    id_set = set(ids)
    print(f"filtering {item.filename} for {len(id_set)} IDs")
    content = src_zip.read(item)
    modified_content, matched_ids = filter_gml_content(content, id_set)

    if matched_ids:
        print(f"  found {len(matched_ids)} matching IDs")
        return modified_content, list(matched_ids)
    else:
        print(f"  no matching IDs found, skipping file")
        return None, []


def filter_gml_objects(src_zip, dst_zip, filter_dict):
    all_matched_ids = []
    normalized_filter = normalize_filter_paths(filter_dict)

    with zipfile.ZipFile(src_zip, 'r') as src, zipfile.ZipFile(dst_zip, 'w', zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.is_dir():
                continue

            if item.filename in normalized_filter:
                content, matched_ids = process_filtered_file(src, item, normalized_filter[item.filename])
                if content is not None:
                    dst.writestr(item, content)
                    all_matched_ids.extend(matched_ids)
            elif should_keep_unfiltered_file(item.filename):
                dst.writestr(item, src.read(item))

    if not all_matched_ids:
        raise ValueError("No GML objects matched filter")

    print("written to", dst_zip)