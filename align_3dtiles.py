import json
import struct
from pathlib import Path
from pygltflib import GLTF2

def read_b3dm_batch_table(path):
    try:
        with open(path, 'rb') as f:
            header = f.read(28)
            if header[:4] != b'b3dm':
                return None
            ft_json_len = struct.unpack('I', header[12:16])[0]
            ft_bin_len = struct.unpack('I', header[16:20])[0]
            bt_json_len = struct.unpack('I', header[20:24])[0]
            bt_bin_len = struct.unpack('I', header[24:28])[0]
            ft_len = ft_json_len + ft_bin_len
            bt_len = bt_json_len + bt_bin_len
            if bt_len == 0:
                return None
            f.seek(28 + ft_len)
            bt_data = f.read(bt_len)
            return json.loads(bt_data[:bt_json_len].decode('utf-8'))
    except Exception:
        pass
    return None

def read_glb_metadata(path):
    try:
        gltf = GLTF2().load(str(path))
        if not gltf.extensions or 'EXT_structural_metadata' not in gltf.extensions:
            return None
        ext = gltf.extensions['EXT_structural_metadata']
        if not ext.get('propertyTables'):
            return None
        prop_table = ext['propertyTables'][0]
        properties = prop_table['properties']
        buffer_data = gltf.binary_blob()
        result = {}
        for prop_name, prop_info in properties.items():
            values_bv = gltf.bufferViews[prop_info['values']]
            values_data = buffer_data[values_bv.byteOffset:values_bv.byteOffset + values_bv.byteLength]
            if 'stringOffsets' in prop_info:
                offsets_bv = gltf.bufferViews[prop_info['stringOffsets']]
                offsets_data = buffer_data[offsets_bv.byteOffset:offsets_bv.byteOffset + offsets_bv.byteLength]
                offsets = struct.unpack(f'{offsets_bv.byteLength//4}I', offsets_data)
                values = [values_data[offsets[i]:offsets[i+1]].decode('utf-8') for i in range(len(offsets)-1)]
            else:
                values = [values_data]
            result[prop_name] = values
        return result
    except Exception:
        pass
    return None

def read_tile_file(path):
    if path.suffix == '.glb':
        return read_glb_metadata(path)
    elif path.suffix == '.b3dm':
        return read_b3dm_batch_table(path)
    return None

def features_by_gml_id(batch_data):
    result = {}
    if not batch_data or 'gml_id' not in batch_data:
        return result
    gml_ids = batch_data['gml_id']
    num_features = len(gml_ids)
    for idx in range(num_features):
        gml_id = gml_ids[idx]
        properties = {k: v[idx] if isinstance(v, list) and idx < len(v) else v
                     for k, v in batch_data.items()}
        result[gml_id] = properties
    return result

def dict_zip(dict1, dict2):
    keys = set(dict1.keys()).union(set(dict2.keys()))
    for k in keys:
        yield k, dict1.get(k, None), dict2.get(k, None)

def collect_features(directory):
    features = {}
    for ext in ["*.b3dm", "*.glb"]:
        for file_path in directory.rglob(ext):
            rel_path = file_path.relative_to(directory)
            batch_data = read_tile_file(file_path)
            for gml_id, props in features_by_gml_id(batch_data).items():
                props['_tile'] = str(rel_path)
                features[gml_id] = props
    return features

def align_3dtiles(d1, d2):
    features1 = collect_features(d1)
    features2 = collect_features(d2)
    for gml_id, f1, f2 in dict_zip(features1, features2):
        yield (gml_id, f1, f2)

if __name__ == '__main__':
    d1 = Path("build/08220-3dtiles/fme/tran_lod3")
    d2 = Path("build/08220-3dtiles/output/tran_lod3")
    for gml_id, f1, f2 in align_3dtiles(d1, d2):
        status = "both" if f1 and f2 else ("only1" if f1 else "only2")
        print(f"{gml_id}\t{status}\t{f1.get('_tile') if f1 else ''}\t{f2.get('_tile') if f2 else ''}")
