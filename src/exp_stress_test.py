"""Bonus B2: Stress test suy giảm dữ liệu (Random Dropout & Gaussian Noise) lên Topic A.

Chạy từ gốc repo:
    python -m src.exp_stress_test
"""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from starter.datasets import load_frame
from starter.perturb import random_dropout, gaussian_noise
from starter.projection import project_velo_to_image, velo_to_cam
from src.exp_yaw_sweep import points_in_box, CLASSES


def run_stress_test():
    fr = load_frame("data/kitti_mini", "000011")
    pts_raw = fr["points"][np.isfinite(fr["points"]).all(axis=1)]
    calib = fr["calib"]
    shape = fr["image"].shape
    cam_true = velo_to_cam(pts_raw[:, :3], calib)

    rows = []

    # 1. Random Dropout: keep 1.0, 0.7, 0.5, 0.3
    dropout_levels = [1.0, 0.7, 0.5, 0.3]
    for keep in dropout_levels:
        pts = random_dropout(pts_raw, keep_ratio=keep, seed=42)
        uv, _, mask = project_velo_to_image(pts, calib, shape)
        uv_all = np.full((len(pts), 2), np.nan)
        uv_all[mask] = uv

        # Tính hit_ratio trên các nhãn
        obj_pts = hits = 0
        cam_sub = velo_to_cam(pts[:, :3], calib)
        for obj in fr["labels"]:
            if obj.type not in CLASSES:
                continue
            sel = points_in_box(cam_sub, obj) & mask
            u, v = uv_all[sel, 0], uv_all[sel, 1]
            x1, y1, x2, y2 = obj.bbox
            hits += int(((u >= x1) & (u <= x2) & (v >= y1) & (v <= y2)).sum())
            obj_pts += int(sel.sum())

        rows.append({
            "perturb_type": "random_dropout",
            "level": keep,
            "total_points": len(pts),
            "object_points": obj_pts,
            "hit_ratio": round(hits / obj_pts, 4) if obj_pts else 0,
        })

    # 2. Gaussian Noise: sigma 0.0, 0.02, 0.05, 0.10 m
    noise_levels = [0.0, 0.02, 0.05, 0.10]
    for sig in noise_levels:
        pts = gaussian_noise(pts_raw, sigma_xyz_m=sig, seed=42)
        uv, _, mask = project_velo_to_image(pts, calib, shape)
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

        rows.append({
            "perturb_type": "gaussian_noise",
            "level": sig,
            "total_points": len(pts),
            "object_points": obj_pts,
            "hit_ratio": round(hits / obj_pts, 4) if obj_pts else 0,
        })

    out_csv = Path("results/stress_test_perturb.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"-> Đã ghi stress test ra {out_csv}")

    # Vẽ biểu đồ stress test
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    # Dropout plot
    d_rows = [r for r in rows if r["perturb_type"] == "random_dropout"]
    ax1.plot([r["level"] * 100 for r in d_rows], [r["object_points"] for r in d_rows],
             marker="o", color="blue", label="Điểm trên vật thể")
    ax1.set_xlabel("Tỉ lệ giữ điểm (%)")
    ax1.set_ylabel("Số điểm trên vật thể")
    ax1.set_title("Random Dropout")
    ax1.grid(alpha=0.3)
    ax1.legend()

    # Noise plot
    n_rows = [r for r in rows if r["perturb_type"] == "gaussian_noise"]
    ax2.plot([r["level"] * 100 for r in n_rows], [r["hit_ratio"] * 100 for r in n_rows],
             marker="s", color="crimson", label="Hit ratio (%)")
    ax2.set_xlabel("Độ lệch chuẩn Gaussian σ (cm)")
    ax2.set_ylabel("Hit ratio (%)")
    ax2.set_title("Gaussian Noise")
    ax2.set_ylim(80, 105)
    ax2.grid(alpha=0.3)
    ax2.legend()

    fig.tight_layout()
    out_fig = Path("results/figures/stress_test.png")
    fig.savefig(out_fig, dpi=150)
    print(f"-> Đã lưu biểu đồ ra {out_fig}")


if __name__ == "__main__":
    run_stress_test()

