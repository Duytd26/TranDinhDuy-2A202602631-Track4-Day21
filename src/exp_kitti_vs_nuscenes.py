"""Bonus B5: So sánh độ nhạy của phép chiếu trên cả 2 dataset KITTI và nuScenes.

Chạy từ gốc repo:
    python -m src.exp_kitti_vs_nuscenes
"""
import csv
from pathlib import Path
import numpy as np

from starter.datasets import load_frame
from starter.projection import perturb_extrinsic, project_velo_to_image


def compare_datasets():
    # 1. KITTI 000011
    fr_kitti = load_frame("data/kitti_mini", "000011")
    pts_kitti = fr_kitti["points"][np.isfinite(fr_kitti["points"]).all(axis=1)]
    shape_kitti = fr_kitti["image"].shape  # (375, 1242, 3)
    f_kitti = float(fr_kitti["calib"].P2[0, 0])  # ~721.5 px
    w_kitti = shape_kitti[1]

    # 2. nuScenes scene-0103_010
    fr_nusc = load_frame("data/nuscenes_mini_subset", "scene-0103_010", use_ego_motion=True)
    pts_nusc = fr_nusc["points"][np.isfinite(fr_nusc["points"]).all(axis=1)]
    shape_nusc = fr_nusc["image"].shape  # (900, 1600, 3)
    f_nusc = float(fr_nusc["calib"].P2[0, 0])  # ~1253 px
    w_nusc = shape_nusc[1]

    yaw_levels = [0.0, 0.5, 1.0, 2.0, 3.0]
    rows = []

    for yaw in yaw_levels:
        # Shift lý thuyết:
        shift_kitti = f_kitti * np.tan(np.deg2rad(yaw))
        rel_kitti = (shift_kitti / w_kitti) * 100

        shift_nusc = f_nusc * np.tan(np.deg2rad(yaw))
        rel_nusc = (shift_nusc / w_nusc) * 100

        # Số điểm bên trong ảnh thực tế:
        calib_k = perturb_extrinsic(fr_kitti["calib"], yaw_deg=yaw)
        _, _, mask_k = project_velo_to_image(pts_kitti, calib_k, shape_kitti)

        calib_n = perturb_extrinsic(fr_nusc["calib"], yaw_deg=yaw)
        _, _, mask_n = project_velo_to_image(pts_nusc, calib_n, shape_nusc)

        rows.append({
            "yaw_deg": yaw,
            "kitti_shift_px": round(shift_kitti, 2),
            "kitti_rel_shift_pct": round(rel_kitti, 2),
            "kitti_points_in_fov": int(mask_k.sum()),
            "nusc_shift_px": round(shift_nusc, 2),
            "nusc_rel_shift_pct": round(rel_nusc, 2),
            "nusc_points_in_fov": int(mask_n.sum()),
        })

    out_csv = Path("results/kitti_vs_nuscenes_drift.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"-> Đã ghi so sánh KITTI vs nuScenes ra {out_csv}")
    for r in rows:
        print(r)


if __name__ == "__main__":
    compare_datasets()

