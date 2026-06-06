# backend/track_data.py
"""
Static F1 track profile data.
These values are representative approximations derived from historical F1 telemetry.
They serve as the primary data source for the /api/tracks endpoint and populate
the Track Cluster scatter plot.

Features:
  - base_lap_time_ms  : Clean-air baseline lap time in milliseconds
  - pit_loss_ms       : Average time lost on a pit stop (pit lane delta) in ms
  - tire_deg_ms_per_lap : Average lap-time loss per lap of tire age in ms
  - cluster           : k-Means cluster assignment (0-3)
"""

TRACK_PROFILES = [
    # Cluster 0 — High-speed, moderate deg (Power circuits)
    {"circuit_name": "Bahrain",         "base_lap_time_ms": 95_000, "pit_loss_ms": 24_000, "tire_deg_ms_per_lap": 200, "cluster": 0},
    {"circuit_name": "Jeddah",          "base_lap_time_ms": 88_000, "pit_loss_ms": 22_500, "tire_deg_ms_per_lap": 180, "cluster": 0},
    {"circuit_name": "Monza",           "base_lap_time_ms": 82_000, "pit_loss_ms": 19_000, "tire_deg_ms_per_lap": 150, "cluster": 0},
    {"circuit_name": "Baku",            "base_lap_time_ms": 105_000,"pit_loss_ms": 23_500, "tire_deg_ms_per_lap": 160, "cluster": 0},

    # Cluster 1 — Technical, high-deg (Street / Twisty)
    {"circuit_name": "Monaco",          "base_lap_time_ms": 76_000, "pit_loss_ms": 28_000, "tire_deg_ms_per_lap": 90,  "cluster": 1},
    {"circuit_name": "Singapore",       "base_lap_time_ms": 105_000,"pit_loss_ms": 27_500, "tire_deg_ms_per_lap": 100, "cluster": 1},
    {"circuit_name": "Hungaroring",     "base_lap_time_ms": 81_000, "pit_loss_ms": 25_000, "tire_deg_ms_per_lap": 260, "cluster": 1},
    {"circuit_name": "Barcelona",       "base_lap_time_ms": 78_000, "pit_loss_ms": 24_500, "tire_deg_ms_per_lap": 280, "cluster": 1},

    # Cluster 2 — Mixed, high pit-stop cost (Long pit lanes)
    {"circuit_name": "Silverstone",     "base_lap_time_ms": 90_000, "pit_loss_ms": 31_000, "tire_deg_ms_per_lap": 220, "cluster": 2},
    {"circuit_name": "Spa-Francorchamps","base_lap_time_ms":107_000,"pit_loss_ms": 30_000, "tire_deg_ms_per_lap": 195, "cluster": 2},
    {"circuit_name": "COTA",            "base_lap_time_ms": 98_000, "pit_loss_ms": 29_500, "tire_deg_ms_per_lap": 210, "cluster": 2},
    {"circuit_name": "Mexico City",     "base_lap_time_ms": 80_000, "pit_loss_ms": 29_000, "tire_deg_ms_per_lap": 185, "cluster": 2},

    # Cluster 3 — Outliers (Extreme deg or very short lap)
    {"circuit_name": "Suzuka",          "base_lap_time_ms": 93_000, "pit_loss_ms": 26_000, "tire_deg_ms_per_lap": 300, "cluster": 3},
    {"circuit_name": "Zandvoort",       "base_lap_time_ms": 73_000, "pit_loss_ms": 25_500, "tire_deg_ms_per_lap": 320, "cluster": 3},
    {"circuit_name": "Montreal",        "base_lap_time_ms": 76_000, "pit_loss_ms": 22_000, "tire_deg_ms_per_lap": 130, "cluster": 3},
    {"circuit_name": "Melbourne",       "base_lap_time_ms": 83_000, "pit_loss_ms": 23_000, "tire_deg_ms_per_lap": 145, "cluster": 3},

    # Extra tracks
    {"circuit_name": "Interlagos",      "base_lap_time_ms": 72_000, "pit_loss_ms": 24_000, "tire_deg_ms_per_lap": 240, "cluster": 1},
    {"circuit_name": "Imola",           "base_lap_time_ms": 79_000, "pit_loss_ms": 26_500, "tire_deg_ms_per_lap": 270, "cluster": 1},
    {"circuit_name": "Miami",           "base_lap_time_ms": 91_000, "pit_loss_ms": 25_000, "tire_deg_ms_per_lap": 230, "cluster": 2},
    {"circuit_name": "Las Vegas",       "base_lap_time_ms": 91_500, "pit_loss_ms": 21_000, "tire_deg_ms_per_lap": 170, "cluster": 0},
    {"circuit_name": "Abu Dhabi",       "base_lap_time_ms": 89_000, "pit_loss_ms": 20_500, "tire_deg_ms_per_lap": 190, "cluster": 0},
    {"circuit_name": "Lusail (Qatar)",  "base_lap_time_ms": 84_000, "pit_loss_ms": 23_000, "tire_deg_ms_per_lap": 295, "cluster": 3},
]

CLUSTER_LABELS = {
    0: "Power Circuit",
    1: "Technical/Street",
    2: "Long Pit Lane",
    3: "Extreme Deg",
}
