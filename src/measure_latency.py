"""Bonus B3: Đo latency đúng cách cho LiDAR-Camera Projection Pipeline.
Bỏ lần chạy đầu (warmup), lặp lại 20 lần, báo trung vị p50 và phân vị p95.

Chạy từ gốc repo:
    python -m src.measure_latency
"""
import csv
from pathlib import Path
import time
import numpy as np

from starter.datasets import load_frame
from starter.projection import project_velo_to_image, velo_to_cam
from src.exp_yaw_sweep import points_in_box, CLASSES


def benchmark_pipeline(frame_id: str = "000011", runs: int = 21):
    fr = load_frame("data/kitti_mini", frame_id)
    pts = fr["points"][np.isfinite(fr["points"]).all(axis=1)]
    calib = fr["calib"]
    shape = fr["image"].shape

    durations = []
    print(f"Bắt đầu đo latency trên KITTI frame {frame_id} ({len(pts)} điểm), {runs} lần chạy...")

    for i in range(runs):
        t0 = time.perf_counter()
        
        # Toàn bộ pipeline QA projection:
        uv, depth, mask = project_velo_to_image(pts, calib, shape)
        cam_true = velo_to_cam(pts[:, :3], calib)
        for obj in fr["labels"]:
            if obj.type in CLASSES:
                _ = points_in_box(cam_true, obj)
                
        dt_ms = (time.perf_counter() - t0) * 1000.0
        durations.append(dt_ms)

    # Bỏ lần chạy đầu tiên (warmup)
    measured = np.array(durations[1:])
    p50 = float(np.percentile(measured, 50))
    p95 = float(np.percentile(measured, 95))
    mean = float(np.mean(measured))

    out_csv = Path("results/latency_benchmark.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["run_id", "latency_ms", "is_warmup"])
        for i, val in enumerate(durations):
            writer.writerow([i, round(val, 3), i == 0])

    print(f"-> Đã ghi kết quả ra {out_csv}")
    print(f"Kết quả (20 lần đo thực tế): p50 = {p50:.2f} ms, p95 = {p95:.2f} ms, mean = {mean:.2f} ms")
    return p50, p95


if __name__ == "__main__":
    benchmark_pipeline()
