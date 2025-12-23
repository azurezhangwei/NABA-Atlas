#!/usr/bin/env python3
# Example:
# python run_naba_inference.py -i /path/to/input.vtk -o /path/to/output \
#   -a /path/to/NABA-Atlas -s /path/to/Slicer -n 20 -x 1 \
#   -m "/path/to/Slicer --launch /path/to/FiberTractMeasurements"
# Params:
#   -i: Input tractography data (.vtk/.vtp) in RAS coordinates.
#   -o: Output directory root (case subfolder is created).
#   -a: Atlas root (expects NABA/ORG reg + 800FC folders).
#   -s: 3D Slicer executable path.
#   -t: Optional transform to match subject to atlas size.
#   -r: Registration mode (rig or nonrig).
#   -n: Number of threads (>=1).
#   -x: Use virtual X server via xvfb-run (0/1).
#   -d: Export diffusion measurements (0/1).
#   -m: FiberTractMeasurements CLI module path.
#   -c: Clean temporary files (0 keep, 1 minimal, 2 maximal).
# Author: Wei Zhang

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _run(cmd, check=True):
    print(" ".join(cmd))
    subprocess.run(cmd, check=check)


def _run_with_xvfb(cmd, use_xvfb):
    if use_xvfb:
        cmd = ["xvfb-run", "-a"] + cmd
    _run(cmd)


def _ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def _find_atlas_dirs(atlas_root):
    root = Path(atlas_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Atlas root not found: {root}")

    reg_candidates = [
        "ORG-RegAtlas-100HCP",
        "NABA-RegAtlas",
        "ORG-RegAtlas",
    ]
    fc_candidates = [
        "ORG-800FC-100HCP",
        "NABA-800FC",
        "ORG-800FC",
    ]

    reg_dir = None
    for name in reg_candidates:
        cand = root / name
        if cand.is_dir():
            reg_dir = cand
            break

    fc_dir = None
    for name in fc_candidates:
        cand = root / name
        if cand.is_dir():
            fc_dir = cand
            break

    if reg_dir is None or fc_dir is None:
        raise FileNotFoundError(
            "Atlas root must contain registration and clustering folders "
            f"(found reg={reg_dir}, fc={fc_dir})."
        )

    reg_atlas = reg_dir / "registration_atlas.vtk"
    if not reg_atlas.is_file():
        raise FileNotFoundError(f"registration_atlas.vtk not found in {reg_dir}")

    atlas_p = fc_dir / "atlas.p"
    atlas_vtp = fc_dir / "atlas.vtp"
    if not atlas_p.is_file() or not atlas_vtp.is_file():
        raise FileNotFoundError(f"atlas.p/atlas.vtp not found in {fc_dir}")

    return reg_dir, fc_dir


def _pick_cluster_location_file(fc_dir, script_dir):
    from_atlas = Path(fc_dir) / "cluster_hemisphere_location.txt"
    if from_atlas.is_file():
        return from_atlas
    fallback = Path(script_dir) / "resources" / "cluster_hemisphere_location.txt"
    if not fallback.is_file():
        raise FileNotFoundError(
            "cluster_hemisphere_location.txt not found in atlas or resources."
        )
    return fallback


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run atlas-based inference (registration, clustering, outlier removal, "
            "hemisphere separation, tract aggregation, and optional measurements)."
        )
    )
    parser.add_argument(
        "-i",
        required=True,
        help="Input tractography data stored in VTK (.vtk or .vtp).",
    )
    parser.add_argument(
        "-o",
        required=True,
        help="Output directory to save all inference outputs.",
    )
    parser.add_argument(
        "-a",
        required=True,
        help=(
            "Path to the atlas root folder. Must contain ORG-RegAtlas-100HCP "
            "and ORG-800FC-100HCP (or NABA-RegAtlas and NABA-800FC)."
        ),
    )
    parser.add_argument(
        "-s",
        required=True,
        help="Path to 3D Slicer (e.g., /Applications/Slicer.app/Contents/MacOS/Slicer).",
    )
    parser.add_argument(
        "-t",
        help="Optional transform file to match data to adult brain size.",
    )
    parser.add_argument(
        "-r",
        choices=["rig", "nonrig"],
        default="rig",
        help="Registration mode (default: rig).",
    )
    parser.add_argument(
        "-n",
        type=int,
        default=1,
        help="Number of threads (default: 1).",
    )
    parser.add_argument(
        "-x",
        type=int,
        choices=[0, 1],
        default=0,
        help="Use virtual X server via xvfb-run (default: 0).",
    )
    parser.add_argument(
        "-d",
        type=int,
        choices=[0, 1],
        default=0,
        help="Export diffusion measurements (default: 0).",
    )
    parser.add_argument(
        "-m",
        help="Path to FiberTractMeasurements CLI module in SlicerDMRI.",
    )
    parser.add_argument(
        "-c",
        type=int,
        choices=[0, 1, 2],
        default=0,
        help="Clean temporary files (0 keep all, 1 minimal, 2 maximal).",
    )

    args = parser.parse_args()
    if args.n < 1:
        args.n = 1

    input_file = Path(args.i).resolve()
    if not input_file.is_file():
        print(f"Input file not found: {input_file}", file=sys.stderr)
        return 1

    slicer_path = Path(args.s).resolve()
    if not slicer_path.exists():
        print(f"3D Slicer not found: {slicer_path}", file=sys.stderr)
        return 1

    if args.d == 1 and not args.m:
        print("ERROR: -d requires -m FiberTractMeasurements module path.", file=sys.stderr)
        return 1

    if args.m:
        module_path = Path(args.m).resolve()
        if not module_path.exists():
            print(f"WARNING: FiberTractMeasurements not found: {module_path}")

    reg_dir, fc_dir = _find_atlas_dirs(args.a)
    cluster_location_file = _pick_cluster_location_file(fc_dir, Path(__file__).parent)

    output_root = Path(args.o).resolve()
    _ensure_dir(output_root)

    subject_id = input_file.stem
    output_case = output_root / subject_id
    _ensure_dir(output_case)

    transformed_tracts_dir = output_case / "TransformedTracts"
    registration_dir = output_case / "TractRegistration"
    clustering_root = output_case / "FiberClustering"
    initial_clusters_dir = clustering_root / "InitialClusters"
    outlier_clusters_dir = clustering_root / "OutlierRemovedClusters"
    transformed_clusters_dir = clustering_root / "TransformedClusters" / subject_id
    separated_clusters_dir = clustering_root / "SeparatedClusters"
    inverse_transformed_dir = output_case / "InvTransformedTracts"
    anatomical_tracts_dir = output_case / "AnatomicalTracts"

    active_input = input_file

    if args.t:
        if not Path(args.t).is_file():
            print(f"Transform file not found: {args.t}", file=sys.stderr)
            return 1
        _ensure_dir(transformed_tracts_dir)
        cmd = [
            "wm_harden_transform.py",
            "-t",
            str(Path(args.t).resolve()),
            str(input_file.parent),
            str(transformed_tracts_dir),
            str(slicer_path),
        ]
        _run_with_xvfb(cmd, args.x == 1)

        transformed = transformed_tracts_dir / input_file.name
        if not transformed.is_file():
            print("ERROR: Transformed input not found.", file=sys.stderr)
            return 1
        active_input = transformed

    _ensure_dir(registration_dir)
    reg_subject_dir = registration_dir / subject_id
    reg_output = reg_subject_dir / "output_tractography" / f"{subject_id}_reg.vtk"
    nonrig_subject = None
    if args.r == "rig":
        if not reg_output.is_file():
            cmd = [
                "wm_register_to_atlas_new.py",
                "-mode",
                "rigid_affine_fast",
                str(active_input),
                str(reg_dir / "registration_atlas.vtk"),
                str(registration_dir),
            ]
            _run(cmd)
    else:
        if not reg_output.is_file():
            cmd = [
                "wm_register_to_atlas_new.py",
                "-mode",
                "affine",
                str(active_input),
                str(reg_dir / "registration_atlas.vtk"),
                str(registration_dir),
            ]
            _run(cmd)

        nonrig_subject = registration_dir / f"{subject_id}_reg"
        reg_output = nonrig_subject / "output_tractography" / f"{subject_id}_reg_reg.vtk"
        if not reg_output.is_file():
            affine_output = reg_subject_dir / "output_tractography" / f"{subject_id}_reg.vtk"
            cmd = [
                "wm_register_to_atlas_new.py",
                "-mode",
                "nonrigid",
                str(affine_output),
                str(reg_dir / "registration_atlas.vtk"),
                str(registration_dir),
            ]
            _run(cmd)

    if not reg_output.is_file():
        print("ERROR: Registration output not found.", file=sys.stderr)
        return 1

    _ensure_dir(initial_clusters_dir)
    fc_case_id = reg_output.stem
    cluster_output = initial_clusters_dir / fc_case_id / "cluster_00800.vtp"
    if not cluster_output.is_file():
        cmd = [
            "wm_cluster_from_atlas.py",
            "-j",
            str(args.n),
            str(reg_output),
            str(fc_dir),
            str(initial_clusters_dir),
            "-norender",
        ]
        _run(cmd)

    _ensure_dir(outlier_clusters_dir)
    outlier_dir = outlier_clusters_dir / f"{fc_case_id}_outlier_removed"
    outlier_output = outlier_dir / "cluster_00800.vtp"
    if not outlier_output.is_file():
        cmd = [
            "wm_cluster_remove_outliers.py",
            "-j",
            str(args.n),
            str(initial_clusters_dir / fc_case_id),
            str(fc_dir),
            str(outlier_clusters_dir),
        ]
        _run(cmd)

    assess_log = outlier_dir / "cluster_location_by_hemisphere.log"
    if not assess_log.is_file():
        cmd = [
            "wm_assess_cluster_location_by_hemisphere.py",
            "-clusterLocationFile",
            str(cluster_location_file),
            str(outlier_dir),
        ]
        _run(cmd)

    _ensure_dir(transformed_clusters_dir)
    transformed_dir = transformed_clusters_dir
    if args.r == "rig":
        tfm = (
            reg_subject_dir
            / "output_tractography"
            / f"itk_txform_{subject_id}.tfm"
        )
        if not tfm.is_file():
            print(f"ERROR: Registration transform not found: {tfm}", file=sys.stderr)
            return 1
        transformed_check = transformed_dir / "cluster_00800.vtp"
        if not transformed_check.is_file():
            cmd = [
                "wm_harden_transform.py",
                "-i",
                "-t",
                str(tfm),
                str(outlier_dir),
                str(transformed_dir),
                str(slicer_path),
            ]
            _run_with_xvfb(cmd, args.x == 1)
    else:
        tfm_nonrig = (
            nonrig_subject
            / "output_tractography"
            / f"itk_txform_{subject_id}_reg.tfm"
        )
        tfm_affine = (
            reg_subject_dir
            / "output_tractography"
            / f"itk_txform_{subject_id}.tfm"
        )
        if not tfm_nonrig.is_file():
            print(f"ERROR: Nonrigid transform not found: {tfm_nonrig}", file=sys.stderr)
            return 1
        if not tfm_affine.is_file():
            print(f"ERROR: Affine transform not found: {tfm_affine}", file=sys.stderr)
            return 1
        temp_dir = transformed_dir / "tmp"
        _ensure_dir(temp_dir)
        temp_check = temp_dir / "cluster_00800.vtp"
        if not temp_check.is_file():
            cmd = [
                "wm_harden_transform.py",
                "-i",
                "-t",
                str(tfm_nonrig),
                str(outlier_dir),
                str(temp_dir),
                str(slicer_path),
            ]
            _run_with_xvfb(cmd, args.x == 1)
        transformed_check = transformed_dir / "cluster_00800.vtp"
        if not transformed_check.is_file():
            cmd = [
                "wm_harden_transform.py",
                "-i",
                "-t",
                str(tfm_affine),
                str(temp_dir),
                str(transformed_dir),
                str(slicer_path),
            ]
            _run_with_xvfb(cmd, args.x == 1)

    transformed_check = transformed_dir / "cluster_00800.vtp"
    if not transformed_check.is_file():
        print("ERROR: Transformed clusters not found.", file=sys.stderr)
        return 1

    _ensure_dir(separated_clusters_dir)
    separate_check = separated_clusters_dir / "tracts_commissural" / "cluster_00800.vtp"
    if not separate_check.is_file():
        cmd = [
            "wm_separate_clusters_by_hemisphere.py",
            str(transformed_dir),
            str(separated_clusters_dir),
        ]
        _run(cmd)

    if args.t:
        tfm_file = Path(args.t).resolve()
        if not tfm_file.is_file():
            print(f"Transform file not found: {tfm_file}", file=sys.stderr)
            return 1
        _ensure_dir(inverse_transformed_dir)
        for cluster_dir in sorted(separated_clusters_dir.iterdir()):
            if not cluster_dir.is_dir():
                continue
            out_dir = inverse_transformed_dir / cluster_dir.name
            _ensure_dir(out_dir)
            out_check = out_dir / "cluster_00800.vtp"
            if out_check.is_file():
                continue
            cmd = [
                "wm_harden_transform.py",
                "-i",
                "-t",
                str(tfm_file),
                str(cluster_dir),
                str(out_dir),
                str(slicer_path),
            ]
            _run_with_xvfb(cmd, args.x == 1)

    final_clusters_dir = inverse_transformed_dir if args.t else separated_clusters_dir

    _ensure_dir(anatomical_tracts_dir)
    append_check = anatomical_tracts_dir / "T_UF_right.vtp"
    if not append_check.is_file():
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "wm_append_clusters_to_anatomical_tracts_naba.py"),
            str(final_clusters_dir),
            str(fc_dir),
            str(anatomical_tracts_dir),
        ]
        _run(cmd)

    if args.d == 1:
        slicer_cmd = f"{slicer_path} --launch {Path(args.m).resolve()}"
        if args.x == 1:
            slicer_cmd = f"xvfb-run -a {slicer_cmd}"

        clusters = {
            "commissural": final_clusters_dir / "tracts_commissural",
            "left": final_clusters_dir / "tracts_left_hemisphere",
            "right": final_clusters_dir / "tracts_right_hemisphere",
        }
        for name, input_dir in clusters.items():
            out_csv = separated_clusters_dir / f"diffusion_measurements_{name}.csv"
            if not out_csv.is_file():
                cmd = [
                    "wm_diffusion_measurements.py",
                    str(input_dir),
                    str(out_csv),
                    slicer_cmd,
                ]
                _run(cmd)

        tracts_csv = anatomical_tracts_dir / "diffusion_measurements_anatomical_tracts.csv"
        if not tracts_csv.is_file():
            cmd = [
                "wm_diffusion_measurements.py",
                str(anatomical_tracts_dir),
                str(tracts_csv),
                slicer_cmd,
            ]
            _run(cmd)

    if args.c >= 1:
        if initial_clusters_dir.exists():
            shutil.rmtree(initial_clusters_dir)
        transformed_root = clustering_root / "TransformedClusters"
        if transformed_root.exists():
            shutil.rmtree(transformed_root)

    if args.c >= 2:
        if registration_dir.exists():
            for vtk_file in registration_dir.glob("*/*/output_tractography/*.vtk"):
                vtk_file.unlink()
            for iteration_dir in registration_dir.glob("*/*/iteration*"):
                shutil.rmtree(iteration_dir)
        if initial_clusters_dir.exists():
            shutil.rmtree(initial_clusters_dir)
        if outlier_clusters_dir.exists():
            for item in outlier_clusters_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        transformed_root = clustering_root / "TransformedClusters"
        if transformed_root.exists():
            for item in transformed_root.rglob("*"):
                if item.is_dir():
                    continue
                item.unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
