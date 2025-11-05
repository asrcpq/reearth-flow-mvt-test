#!/usr/bin/env python3
import sys, json, subprocess, os, zipfile, shutil
from pathlib import Path
from align_mvt import align_mvt
from geometry_comparison import compare_polygons, compare_lines
from run_workflow import main as run_workflow_main
from filter_gml import filter_gml_objects

REEARTH_DIR = Path("/Users/tsq/Projects/reearth-flow")
ROOT = Path(__file__).parent
PLATEAU_ROOT = Path(os.getenv("HOME")) / "Projects" / "gkk"

def run_test(profile_path, stages):
	profile_path = Path(profile_path)
	profile = json.load(open(profile_path))
	test_name = profile_path.parent.name

	TEST_DIR = profile_path.parent
	original_citygml_path = PLATEAU_ROOT / profile["citygml_plateau"]
	BUILD_DIR = ROOT / "build" / test_name
	OUTPUT_DIR = BUILD_DIR / "output"
	FME_DIR = BUILD_DIR / "fme"

	print(f"Running	test: {test_name}")
	print(f"Stages: {stages}")
	OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

	data_script = TEST_DIR / "data.py"
	needs_processing = ("filter" in profile and profile["filter"]) or data_script.exists()
	citygml_path = BUILD_DIR / original_citygml_path.name
	if not needs_processing:
		citygml_path = original_citygml_path
	elif "g" in stages:
		if "filter" in profile and profile["filter"]:
			print(f"Creating filtered GML with objects: {profile['filter']}")
			filter_gml_objects(original_citygml_path, citygml_path, profile["filter"])
		elif data_script.exists():
			print(f"Running data preparation: {data_script}")
			subprocess.run([sys.executable, str(data_script), str(citygml_path)], check=True)

	# Extract FME output
	if "f" in stages:
		try:
			shutil.rmtree(FME_DIR)
		except FileNotFoundError:
			pass
		fme_zip = ROOT / profile['fme_output']
		if not fme_zip.exists():
			raise FileNotFoundError(f"FME output zip not found: {fme_zip}")
		print(f"Extracting FME output: {fme_zip} -> {FME_DIR}")
		FME_DIR.mkdir(parents=True, exist_ok=True)
		with zipfile.ZipFile(fme_zip, 'r') as zip_ref:
			zip_ref.extractall(FME_DIR)
		for mvt_file in FME_DIR.rglob("*.mvt"):
			mvt_file.rename(mvt_file.with_suffix(".pbf"))

	# Stage "r": Workflow running
	if "r" in stages:
		workflow = REEARTH_DIR / profile["workflow_path"]
		if not workflow.exists():
			raise FileNotFoundError(f"Workflow not found: {workflow}")
		run_workflow_main(citygml_path, workflow, REEARTH_DIR, BUILD_DIR, OUTPUT_DIR)

	if "e" in stages:
		tests = profile.get("tests", {})
		print(f"Comparing: {FME_DIR} vs {OUTPUT_DIR}")

		all_passed = True
		for name, cfg in tests.items():
			thresh = cfg.get("threshold", 0.0)
			zoom = cfg.get("zoom")
			zmin = zoom[0] if zoom else None
			zmax = zoom[1] if zoom else None

			results = []
			worst = 0.0
			fails = 0

			for path, gid, g1, g2 in align_mvt(FME_DIR, OUTPUT_DIR, zmin, zmax):
				is_poly = (g1 or g2) and (g1 or g2).geom_type in ('Polygon', 'MultiPolygon')

				if name == "compare_polygons" and is_poly:
					status, score = compare_polygons(g1, g2)
				elif name == "compare_lines":
					status, score = compare_lines(g1, g2)
				else:
					continue

				worst = max(worst, score)
				if score > thresh:
					fails += 1
				results.append((score, path, gid, status))

			if fails > 0:
				all_passed = False

			print(f"\n{name}: {len(results)} total, {fails} failed")
			if fails > 0:
				print(f"  \x1b[31mworst: {worst:.6f}\x1b[0m")
			else:
				print(f"  worst: {worst:.6f}")

			print(f"  Worst 5:")
			for score, path, gid, status in sorted(results, reverse=True)[:5]:
				print(f"    {path} | {gid} | {score:.6f} | {status}")

		print("\nTest PASSED" if all_passed else "\nTest FAILED")

		# generate output_list
		output_layers = sorted({p.relative_to(OUTPUT_DIR).parts[0] for p in OUTPUT_DIR.rglob("*.pbf")}) if OUTPUT_DIR.exists() else []
		fme_layers = sorted({p.relative_to(FME_DIR).parts[0] for p in FME_DIR.rglob("*.pbf")}) if FME_DIR.exists() else []
		with open(BUILD_DIR / "output_list", 'w') as f:
			for layer in sorted(set(output_layers + fme_layers)):
				if layer in output_layers: f.write(f"output/{layer}/{{z}}/{{x}}/{{y}}.pbf\n")
				if layer in fme_layers: f.write(f"fme/{layer}/{{z}}/{{x}}/{{y}}.pbf\n")
		print(f"Generated: {BUILD_DIR / 'output_list'}")

stages = sys.argv[2] if len(sys.argv) > 2 else "re"
run_test(Path(sys.argv[1]).resolve(), stages)
