import toml

def recursive_update(d, updates):
    for key, value in d.items():
        if isinstance(value, dict):
            recursive_update(value, updates)
        if key in updates:
            d[key] = updates[key]
    # Also check nested dicts inside lists
    for k, v in d.items():
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    recursive_update(item, updates)

def update_toml_file(file_path, updates):
    with open(file_path, 'r') as f:
        data = toml.load(f)
    recursive_update(data, updates)
    with open(file_path, 'w') as f:
        toml.dump(data, f)

updates = {
"nusamai-citygml": { "path": "../../plateau-gis-converter/nusamai-citygml", "features": ["serde", "serde_json"] },
"nusamai-czml": { "path": "../../plateau-gis-converter/nusamai-czml" },
"nusamai-gltf": { "path": "../../plateau-gis-converter/nusamai-gltf" },
"nusamai-plateau": { "path": "../../plateau-gis-converter/nusamai-plateau", "features": ["serde"] },
"nusamai-projection": { "path": "../../plateau-gis-converter/nusamai-projection" },
"nusamai-shapefile": { "path": "../../plateau-gis-converter/nusamai-shapefile" },
# "tinymvt": { "path": "../../tinymvt" },
}
update_toml_file("/Users/tsq/Projects/reearth-flow/engine/Cargo.toml", updates)
