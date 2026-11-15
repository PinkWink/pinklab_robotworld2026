"""Odometry vs ground truth on the square drive (1 lap, 3 laps). Input: artifacts/dev/odom_square{1,3}.csv from odom_experiment.py."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

if any(f.name == "NanumGothic" for f in font_manager.fontManager.ttflist):
    plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

for laps in (1, 3):
    a = np.genfromtxt(f"artifacts/dev/odom_square{laps}.csv", delimiter=",", names=True)
    dist = np.r_[0, np.cumsum(np.hypot(np.diff(a["true_x"]), np.diff(a["true_y"])))]
    err = np.hypot(a["odom_x"] - a["true_x"], a["odom_y"] - a["true_y"]) * 100
    yaw = np.degrees((a["odom_yaw"] - a["true_yaw"] + np.pi) % (2 * np.pi) - np.pi)
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(14, 5.2), dpi=150, gridspec_kw={"width_ratios": [1, 1.5]})
    ax.plot(a["true_x"], a["true_y"], color="#2e7d32", lw=2.6, label="ground truth (출발 자세 기준)")
    ax.plot(a["odom_x"], a["odom_y"], color="#1f4e79", lw=1.3, ls="--", label="/odom (바퀴 적분)")
    ax.plot(0, 0, "ko"); ax.annotate("출발 (0, 0)", (0, 0), (0.03, -0.09), fontsize=9)
    ax.plot(a["odom_x"][-1], a["odom_y"][-1], "s", color="#1f4e79")
    ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.legend(loc="upper left", fontsize=9)
    ax.set_title(f"사각형 {laps}바퀴 (한 변 1 m): 두 경로가 거의 겹친다", fontsize=11)
    bx.plot(dist, err, color="#C62828", lw=1.6)
    bx.grid(alpha=0.3); bx.set_xlabel("주행 거리 [m] (ground truth)"); bx.set_ylabel("위치 오차 |odom - truth| [cm]")
    bx.set_title(f"오차 성장: {dist[-1]:.1f} m 주행 후 {err[-1]:.1f} cm · yaw {yaw[-1]:+.2f}°", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"docs/camp/lesson03_odom_square{laps}.png", facecolor="white"); plt.close(fig)
    print(f"saved lesson03_odom_square{laps}.png  dist {dist[-1]:.2f} m  err {err[-1]:.2f} cm  yaw {yaw[-1]:+.2f} deg")
