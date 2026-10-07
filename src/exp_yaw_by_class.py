"""Phần mở rộng Benchmark (mức Good/Advanced):
Phân tích chi tiết tỉ lệ hit_ratio theo loại đối tượng (Car vs Pedestrian) và cự ly.

Chạy từ gốc repo:
    python -m src.exp_yaw_by_class --data-root data/kitti_mini --frames 000008 000011 000049
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from starter.datasets import load_frame
from starter.projection import perturb_extrinsic, project_velo_to_image, velo_to_cam
from src.exp_yaw_sweep import points_in_box

CLASSES = ("Car", "Pedestrian")


def run_one_by_class(fr: dict, yaw_deg: float) -> list[dict]:
    pts = fr["points"][np.isfinite(fr["points"]).all(axis=1)]
    cam_true = velo_to_cam(pts[:, :3], fr["calib"])
    calib = perturb_extrinsic(fr["calib"], yaw_deg=yaw_deg)
    uv, _, mask = project_velo_to_image(pts, calib, fr["image"].shape)
    uv_all = np.full((len(pts), 2), np.nan)
    uv_all[mask] = uv

    stats = {c: {"hits": 0, "obj_pts": 0} for c in CLASSES}
    for obj in fr["labels"]:
        if obj.type not in CLASSES:
            continue
        sel = points_in_box(cam_true, obj) & mask
        u, v = uv_all[sel, 0], uv_all[sel, 1]
        x1, y1, x2, y2 = obj.bbox
        hits = int(((u >= x1) & (u <= x2) & (v >= y1) & (v <= y2)).sum())
        obj_pts = int(sel.sum())
        stats[obj.type]["hits"] += hits
        stats[obj.type]["obj_pts"] += obj_pts

    records = []
    for c in CLASSES:
        op = stats[c]["obj_pts"]
        h = stats[c]["hits"]
        if op > 0:
            records.append({
                "class": c,
                "yaw_deg": yaw_deg,
                "object_points": op,
                "hit_ratio": round(h / op, 4),
            })
    return records


def main() -> None:
    ap = argparse.ArgumentParser(description="Quét yaw theo từng class đối tượng")
    ap.add_argument("--data-root", default="data/kitti_mini")
    ap.add_argument("--frames", nargs="+", default=["000008", "000011", "000049"])
    ap.add_argument("--yaw-levels", nargs="+", type=float, default=[0, 0.5, 1, 2, 3])
    ap.add_argument("--out", default="results/yaw_by_class_sweep.csv")
    args = ap.parse_args()

    rows = []
    for frame in args.frames:
        fr = load_frame(args.data_root, frame)
        for yaw in args.yaw_levels:
            rec = run_one_by_class(fr, yaw)
            for r in rec:
                rows.append({"frame": frame, **r})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    print(f"-> {out} ({len(df)} dòng)")

    # Tính trung bình theo class
    summary = df.groupby(["class", "yaw_deg"])["hit_ratio"].mean().reset_index()
    print("\n=== TRUNG BÌNH HIT RATIO THEO CLASS ===")
    print(summary.to_string(index=False))

    # Vẽ biểu đồ so sánh Car vs Pedestrian
    fig, ax = plt.subplots(figsize=(6, 4))
    for c, g in summary.groupby("class"):
        ax.plot(g["yaw_deg"], 100 * g["hit_ratio"], marker="s" if c == "Pedestrian" else "o",
                linewidth=2, label=f"Class: {c}")
    ax.axhline(85, color="red", linestyle="--", alpha=0.7, label="Ngưỡng cảnh báo (85%)")
    ax.set_xlabel("Lệch yaw (độ)")
    ax.set_ylabel("% điểm rơi trong 2D box")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig_out = Path("results/figures/yaw_by_class.png")
    fig.savefig(fig_out, dpi=150)
    print(f"-> {fig_out}")


if __name__ == "__main__":
    main()
