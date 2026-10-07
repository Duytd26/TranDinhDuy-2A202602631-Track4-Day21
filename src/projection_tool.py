"""Bonus B4: Reusable CLI Tool cho LiDAR-Camera Projection QA.

Script có giao diện dòng lệnh linh hoạt, đầy đủ help và tham số mặc định hợp lý,
giúp tái sử dụng dễ dàng cho mọi pipeline kiểm thử calibration trong tương lai.

Cách dùng:
    python -m src.projection_tool --help
    python -m src.projection_tool
    python -m src.projection_tool --data-root data/kitti_mini --frame 000011 --yaw-deg 1.5
"""
import argparse
from pathlib import Path
import cv2
import numpy as np

from starter.datasets import load_frame, dataset_type
from starter.projection import (
    perturb_extrinsic,
    project_velo_to_image,
    overlay_points,
    draw_box2d,
    velo_to_cam,
)
from src.exp_yaw_sweep import points_in_box, CLASSES


def run_tool(
    data_root: str = "data/kitti_mini",
    frame: str = "000011",
    yaw_deg: float = 0.0,
    pitch_deg: float = 0.0,
    roll_deg: float = 0.0,
    tx: float = 0.0,
    ty: float = 0.0,
    tz: float = 0.0,
    out_dir: str = "results/figures",
    eval_hit_ratio: bool = True,
) -> dict:
    kwargs = {"use_ego_motion": True} if dataset_type(data_root) == "nuscenes" else {}
    fr = load_frame(data_root, frame, **kwargs)
    pts = fr["points"][np.isfinite(fr["points"]).all(axis=1)]

    # Áp dụng perturb extrinsic nếu có
    calib = perturb_extrinsic(fr["calib"], roll_deg, pitch_deg, yaw_deg, (tx, ty, tz))
    uv, depth, mask = project_velo_to_image(pts, calib, fr["image"].shape)

    # Vẽ overlay
    vis = overlay_points(fr["image"], uv, depth)
    for obj in fr["labels"]:
        vis = draw_box2d(vis, obj.bbox, label=obj.type)

    out_path = Path(out_dir) / f"tool_{frame}_y{yaw_deg}_p{pitch_deg}_r{roll_deg}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis)

    res = {
        "frame": frame,
        "total_points": len(pts),
        "inside_fov": int(mask.sum()),
        "fov_ratio": round(float(mask.mean()), 4),
        "output_image": str(out_path),
    }

    if eval_hit_ratio:
        cam_true = velo_to_cam(pts[:, :3], fr["calib"])
        uv_all = np.full((len(pts), 2), np.nan)
        uv_all[mask] = uv
        obj_pts = hits = 0
        for obj in fr["labels"]:
            if obj.type not in CLASSES:
                continue
            sel = points_in_box(cam_true, obj) & mask
            u, v = uv_all[sel, 0], uv_all[sel, 1]
            x1, y1, x2, y2 = obj.bbox
            hits += int(((u >= x1) & (u <= x2) & (v >= y1) & (v <= y2)).sum())
            obj_pts += int(sel.sum())
        res["object_points"] = obj_pts
        res["hit_ratio"] = round(hits / obj_pts, 4) if obj_pts else None

    return res


def main():
    parser = argparse.ArgumentParser(
        description="LiDAR-Camera Projection & Calibration Drift QA Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--data-root", default="data/kitti_mini", help="Thư mục gốc của dataset (KITTI hoặc nuScenes)")
    parser.add_argument("--frame", default="000011", help="ID của frame cần kiểm tra (ví dụ 000011, scene-0103_010)")
    parser.add_argument("--yaw-deg", type=float, default=0.0, help="Góc xoay lệch trục yaw (độ, quanh trục z LiDAR)")
    parser.add_argument("--pitch-deg", type=float, default=0.0, help="Góc xoay lệch trục pitch (độ, quanh trục y LiDAR)")
    parser.add_argument("--roll-deg", type=float, default=0.0, help="Góc xoay lệch trục roll (độ, quanh trục x LiDAR)")
    parser.add_argument("--tx", type=float, default=0.0, help="Dịch chuyển LiDAR theo trục x (mét)")
    parser.add_argument("--ty", type=float, default=0.0, help="Dịch chuyển LiDAR theo trục y (mét)")
    parser.add_argument("--tz", type=float, default=0.0, help="Dịch chuyển LiDAR theo trục z (mét)")
    parser.add_argument("--out-dir", default="results/figures", help="Thư mục lưu ảnh kết quả overlay")
    parser.add_argument("--no-eval", action="store_true", help="Bỏ qua tính toán hit_ratio đối với nhãn vật thể")

    args = parser.parse_args()
    result = run_tool(
        data_root=args.data_root,
        frame=args.frame,
        yaw_deg=args.yaw_deg,
        pitch_deg=args.pitch_deg,
        roll_deg=args.roll_deg,
        tx=args.tx,
        ty=args.ty,
        tz=args.tz,
        out_dir=args.out_dir,
        eval_hit_ratio=not args.no_eval,
    )

    print("\n=== KẾT QUẢ KIỂM TRA PROJECTION QA ===")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
