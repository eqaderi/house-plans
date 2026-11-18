"""Reproduce derived regional summaries and figures from the saved service responses.

Run with the project Python plus matplotlib in the environment. This script reads
saved research exports only; it does not mutate canonical site/project state.
"""

import calendar
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parent


def read(name):
    return json.loads((ROOT / name).read_text())


c = read("nasa-climatology.json")
h = read("pvgis-horizon.json")
w = read("nasa-hourly-wind-2025.json")
p = c["properties"]["parameter"]
months = [calendar.month_abbr[i].upper() for i in range(1, 13)]
keys = ["T2M", "RH2M", "WS10M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]
with (ROOT / "monthly-regional-climate.csv").open("w") as f:
    writer = csv.writer(f)
    writer.writerow(["month", "mean_temperature_C", "relative_humidity_percent",
                     "wind_speed_10m_m_s", "solar_kWh_m2_day", "precipitation_mm_day"])
    for month in months:
        writer.writerow([month] + [p[k][month] for k in keys])

wp = w["properties"]["parameter"]
times = sorted(wp["WS10M"])
expected = [(datetime(2025, 1, 1) + timedelta(hours=i)).strftime("%Y%m%d%H")
            for i in range(8760)]
assert times == expected == sorted(wp["WD10M"]), "Incomplete 2025 hourly series"
speed = np.array([wp["WS10M"][t] for t in times])
direction = np.array([wp["WD10M"][t] for t in times])
assert np.all(np.isfinite(speed)) and np.all(speed >= 0)
assert np.all(np.isfinite(direction)) and np.all((direction >= 0) & (direction <= 360))
calm = speed < 0.5
sector = (np.floor((direction + 11.25) / 22.5).astype(int) % 16)
names = "N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split()
month_numbers = np.array([int(t[4:6]) for t in times])


def wind_summary(mask):
    count = int(mask.sum())
    noncalm = mask & ~calm
    sectors = []
    for i, name in enumerate(names):
        chosen = noncalm & (sector == i)
        sectors.append({"from": name, "hours": int(chosen.sum()),
                        "percent_all_valid_hours": round(100 * chosen.sum() / count, 3)})
    return {"valid_hours": count, "calm_threshold_m_s": 0.5,
            "calm_percent": round(float(100 * (mask & calm).sum() / count), 3),
            "mean_speed_m_s": round(float(speed[mask].mean()), 3),
            "p95_hourly_speed_m_s": round(float(np.percentile(speed[mask], 95)), 3),
            "largest_hourly_mean_m_s": round(float(speed[mask].max()), 3),
            "sectors": sorted(sectors, key=lambda v: v["hours"], reverse=True)}


summaries = {"annual_2025": wind_summary(np.ones(8760, dtype=bool))}
for season, numbers in {"DJF": [12, 1, 2], "MAM": [3, 4, 5],
                        "JJA": [6, 7, 8], "SON": [9, 10, 11]}.items():
    summaries[season] = wind_summary(np.isin(month_numbers, numbers))

horizon = h["outputs"]["horizon_profile"]
solar = {"horizon_min_deg": min(r["H_hor"] for r in horizon),
         "horizon_max_deg": max(r["H_hor"] for r in horizon),
         "winter_noon_height_deg": max(r["H_sun(w)"] for r in h["outputs"]["winter_solstice"]),
         "summer_noon_height_deg": max(r["H_sun(s)"] for r in h["outputs"]["summer_solstice"])}
summary = {"status": "regional_model_and_terrain_simulation; not on-site measurements",
           "wind_direction": "FROM; degrees clockwise from true north; 16 sectors centred on 22.5-degree steps",
           "wind_denominator": "All valid hours including calm; calm omitted from directional sectors",
           "wind": summaries, "sun_and_horizon": solar,
           "rainfall_status": "Unvalidated regional estimate; do not use for drainage sizing",
           "model_precip_approx_annual_mm": round(p["PRECTOTCORR"]["ANN"] * 365, 1)}
(ROOT / "derived-summary.json").write_text(json.dumps(summary, indent=2) + "\n")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "#faf9f5", "axes.facecolor": "#faf9f5"})
fig, ax = plt.subplots(figsize=(11.5, 6.3), layout="constrained")
az = np.array([r["A"] for r in horizon])
height = np.array([r["H_hor"] for r in horizon])
ax.fill_between(az, 0, height, color="#b2b9ab", alpha=.7, label="Modelled mountain horizon")
ax.plot(az, height, color="#52664b", linewidth=1.5)
for name, suffix, color, label in [("winter_solstice", "w", "#367eaa", "Winter solstice · midday 31.6°"),
                                    ("summer_solstice", "s", "#c68526", "Summer solstice · midday 78.5°")]:
    rows = [r for r in h["outputs"][name] if r[f"H_sun({suffix})"] > 0]
    ax.plot([r[f"A_sun({suffix})"] for r in rows],
            [r[f"H_sun({suffix})"] for r in rows], color=color, linewidth=2.8,
            marker=".", markersize=4, label=label)
ax.set(ylim=(0, 90), xlim=(-180, 180), ylabel="Angle above level horizon (degrees)",
       title="Sun paths and the surrounding mountains")
ax.set_xticks([-180, -135, -90, -45, 0, 45, 90, 135, 180],
              ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"])
ax.set_xlabel("Direction you face · east / morning at left, west / afternoon at right")
ax.grid(axis="y", alpha=.2)
ax.legend(loc="upper left", frameon=False)
fig.suptitle("Your field · preliminary terrain and solar study", fontsize=18, fontweight="bold")
fig.text(.5, -.035, "PVGIS 5.3, DEM horizon at rounded query position. Buildings, trees and proposed retaining walls excluded.\n"
         "Curves show solar geometry, not hours of sunshine. Owner supplied EPSG:32638 and recognised the map point.",
         ha="center", fontsize=10, color="#555555")
fig.savefig(ROOT / "sun-and-mountains.png", dpi=170, bbox_inches="tight")
fig.savefig(ROOT / "sun-and-mountains.svg", bbox_inches="tight")
plt.close(fig)

fig = plt.figure(figsize=(12, 8.5), layout="constrained")
gs = fig.add_gridspec(2, 2, width_ratios=[1.15, 1])
a = fig.add_subplot(gs[0, 0])
a.plot(range(12), [p["T2M"][m] for m in months], color="#ba5d37", marker="o", linewidth=2)
a.set_xticks(range(12), [m.title()[0] for m in months])
a.set(ylabel="Monthly mean temperature (°C)", ylim=(-3, 33), title="Cold winter, hot summer")
a.axhline(0, color="gray", linewidth=.7, linestyle="--")
a.grid(axis="y", alpha=.2)
a = fig.add_subplot(gs[1, 0])
a.bar(range(12), [p["ALLSKY_SFC_SW_DWN"][m] for m in months], color="#c99d38", width=.65)
a.set_xticks(range(12), [m.title()[0] for m in months])
a.set(ylabel="Solar energy (kWh/m²/day)", ylim=(0, 9.5), title="Regional sunlight energy · horizontal surface")
a.grid(axis="y", alpha=.2)
a.text(.03, .94, "2001–2025 climatology\nEnergy is not sunshine duration", transform=a.transAxes,
       va="top", fontsize=10, color="#555555")
a = fig.add_subplot(gs[:, 1], projection="polar")
a.set_theta_zero_location("N")
a.set_theta_direction(-1)
frequencies = np.array([100 * ((sector == i) & ~calm).sum() / 8760 for i in range(16)])
a.bar(np.deg2rad(np.arange(16) * 22.5), frequencies, width=np.deg2rad(19), color="#528f9b", alpha=.9)
a.set_xticks(np.deg2rad(np.arange(0, 360, 45)), ["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
a.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
a.set_rlabel_position(100)
a.set_title("2025 regional wind · direction FROM\nShare of all 8,760 hours", pad=26)
a.text(.5, -.13, f"Mean speed {speed.mean():.2f} m/s at 10 m\nCalm (<0.5 m/s): {100*calm.mean():.1f}%\nOne model year; local hillside winds may differ",
       transform=a.transAxes, ha="center", va="top", fontsize=10, color="#555555")
fig.suptitle("Regional climate context for your field", fontsize=18, fontweight="bold")
fig.text(.5, -.055, "NASA POWER / MERRA-2 and SYN1DEG. Broad grid cells; model elevation 1,521 m, survey points 1,665–1,680 m.\n"
         "Temperature and wind are preliminary context. Rainfall, snow, frost and engineering design extremes require local verification.",
         ha="center", fontsize=10, color="#555555")
fig.savefig(ROOT / "regional-climate-and-wind.png", dpi=170, bbox_inches="tight")
fig.savefig(ROOT / "regional-climate-and-wind.svg", bbox_inches="tight")
plt.close(fig)
print(json.dumps({"sun": solar, "wind": {k: {q: v[q] for q in ["valid_hours", "mean_speed_m_s", "calm_percent", "sectors"]}
                                          for k, v in summaries.items()}}, indent=2))
