
import numpy as np
import pandas as pd

DEMAND_THRESHOLD_KW = 160.0
CRITICAL_THRESHOLD_KW = 200.0
PEAK_START_HOUR = 18
PEAK_END_HOUR = 22


def determine_grid_mode(timestamp, predicted_demand_kw):
    """
    Determine grid operating mode using HackSphere rules.

    Renewable Storage Mode:
      - Predicted demand > 160 kW, OR
      - Hour is between 18:00 and 22:00 inclusive.

    Critical overload alert:
      - Predicted demand >= 200 kW.
    """

    try:
        timestamp = pd.to_datetime(timestamp, errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid timestamp: {timestamp}") from exc

    try:
        demand = float(predicted_demand_kw)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Invalid predicted demand: {predicted_demand_kw}"
        ) from exc

    if not np.isfinite(demand) or demand < 0:
        raise ValueError(
            "Predicted demand must be a finite, non-negative number."
        )

    is_peak_hour = PEAK_START_HOUR <= timestamp.hour <= PEAK_END_HOUR
    high_demand = demand > DEMAND_THRESHOLD_KW
    critical_overload = demand >= CRITICAL_THRESHOLD_KW

    if high_demand or is_peak_hour:
        mode = "Renewable Storage Mode"
    else:
        mode = "Main Grid Mode"

    return {
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "predicted_demand_kw": round(demand, 2),
        "grid_mode": mode,
        "critical_overload": critical_overload,
        "alert": (
            "CRITICAL OVERLOAD"
            if critical_overload
            else None
        ),
    }


def build_forecast(input_df, predictions):
    """Combine input records, predictions, and grid decisions."""

    if "timestamp" not in input_df.columns:
        raise ValueError("Input data must contain a timestamp column.")

    if len(input_df) != len(predictions):
        raise ValueError(
            "The number of predictions must match the input records."
        )

    if len(input_df) == 0:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "predicted_demand_kw",
                "grid_mode",
                "critical_overload",
                "alert",
            ]
        )

    results = [
        determine_grid_mode(timestamp, demand)
        for timestamp, demand in zip(
            input_df["timestamp"], predictions
        )
    ]

    return pd.DataFrame(results)


if __name__ == "__main__":
    test_cases = [
        # Demand boundary tests
        ("2026-10-24 12:00:00", 150),   # Main Grid
        ("2026-10-24 12:00:00", 160),   # Main Grid
        ("2026-10-24 12:00:00", 160.01),# Renewable
        ("2026-10-24 12:00:00", 200),   # Renewable + critical

        # Peak-hour tests
        ("2026-10-24 17:00:00", 150),   # Main Grid
        ("2026-10-24 18:00:00", 150),   # Renewable
        ("2026-10-24 22:00:00", 150),   # Renewable
        ("2026-10-24 23:00:00", 150),   # Main Grid
    ]

    print("Smart Grid Controller Boundary Tests\n")

    for timestamp, demand in test_cases:
        print(determine_grid_mode(timestamp, demand))

