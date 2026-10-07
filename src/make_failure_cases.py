"""Tạo ảnh minh hoạ failure cases chất lượng cao cho CP4.

Chạy từ gốc repo:
    python -m src.make_failure_cases
"""
from pathlib import Path

import cv2
import numpy as np

from starter.datasets import load_frame
from starter.projection import (
    draw_box2d,
    overlay_points,
    perturb_extrinsic,
    project_velo_to_image,
)

OUT_DIR = Path("results/figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def create_geometry_failure() -> None:
    """Tạo failure case Geometry: Lệch yaw 2 độ trên KITTI frame 000011."""
    fr = load_frame("data/kitti_mini", "000011")

    # 1. Baseline: yaw 0 deg
    calib_ok = fr["calib"]
    uv_ok, depth_ok, _ = project_velo_to_image(fr["points"], calib_ok, fr["image"].shape)
    vis_ok = overlay_points(fr["image"], uv_ok, depth_ok)
    for obj in fr["labels"]:
        vis_ok = draw_box2d(vis_ok, obj.bbox, label=obj.type)

    # 2. Perturbed: yaw 2 deg
    calib_fail = perturb_extrinsic(fr["calib"], yaw_deg=2.0)
    uv_fail, depth_fail, _ = project_velo_to_image(fr["points"], calib_fail, fr["image"].shape)
    vis_fail = overlay_points(fr["image"], uv_fail, depth_fail)
    for obj in fr["labels"]:
        vis_fail = draw_box2d(vis_fail, obj.bbox, label=obj.type)

    # Thêm tiêu đề text lên ảnh
    cv2.putText(vis_ok, "BASELINE (Yaw 0 deg - Hit 99.5%)", (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    cv2.putText(vis_fail, "FAIL: GEOMETRY (Yaw 2 deg - Hit 45.4%)", (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    # Crop vùng người đi bộ trung tâm (u: 350-750, v: 140-340) để quan sát chi tiết
    # và ghép toàn cảnh trên/dưới
    h, w = fr["image"].shape[:2]
    combined = np.vstack([vis_ok, vis_fail])

    out_path = OUT_DIR / "fail_01_yaw_2deg_pedestrian.png"
    cv2.imwrite(str(out_path), combined)
    print(f"-> {out_path} ({combined.shape[1]}x{combined.shape[0]})")


def create_time_failure() -> None:
    """Tạo failure case Time: nuScenes scene-0103_010 khi tắt bù chuyển động ego-motion."""
    fr_ok = load_frame("data/nuscenes_mini_subset", "scene-0103_010", use_ego_motion=True)
    uv_ok, depth_ok, mask_ok = project_velo_to_image(fr_ok["points"], fr_ok["calib"], fr_ok["image"].shape)
    vis_ok = overlay_points(fr_ok["image"], uv_ok, depth_ok)
    for obj in fr_ok["labels"]:
        vis_ok = draw_box2d(vis_ok, obj.bbox, label=obj.type)

    fr_fail = load_frame("data/nuscenes_mini_subset", "scene-0103_010", use_ego_motion=False)
    uv_fail, depth_fail, mask_fail = project_velo_to_image(fr_fail["points"], fr_fail["calib"], fr_fail["image"].shape)
    vis_fail = overlay_points(fr_fail["image"], uv_fail, depth_fail)
    for obj in fr_fail["labels"]:
        vis_fail = draw_box2d(vis_fail, obj.bbox, label=obj.type)

    cv2.putText(vis_ok, f"WITH EGO MOTION (Points inside: {int(mask_ok.sum())})", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    cv2.putText(vis_fail, f"FAIL: TIME - NO EGO MOTION (Points: {int(mask_fail.sum())})", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    # Resize để ghép đôi side-by-side dễ nhìn
    vis_ok_small = cv2.resize(vis_ok, (800, 450))
    vis_fail_small = cv2.resize(vis_fail, (800, 450))
    combined = np.hstack([vis_ok_small, vis_fail_small])

    out_path = OUT_DIR / "fail_02_nusc_no_ego_motion.png"
    cv2.imwrite(str(out_path), combined)
    print(f"-> {out_path} ({combined.shape[1]}x{combined.shape[0]})")


def main() -> None:
    create_geometry_failure()
    create_time_failure()


if __name__ == "__main__":
    main()
