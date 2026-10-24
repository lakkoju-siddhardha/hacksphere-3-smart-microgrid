
import pandas as pd


DEMAND_THRESHOLD_KW = 160.0
CRITICAL_THRESHOLD_KW = 200.0
PEAK_START_HOUR = 18
PEAK_END_HOUR = 22


def determine_grid_mode(timestamp, predicted_demand_kw):
    """
    Determine the grid operating mode from the project rules.

    Renewable Storage Mode:
      - Demand > 160 kW, OR
      - Hour is between 18:00 and 22:00 inclusive.

    Critical overload alert:
      - Demand >= 200 kW.
    """

    timestamp = pd.to_datetime(timestamp)
    demand = float(predicted_demand_kw)

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
    """Combine input records, predictions, and grid-control decisions."""

    if len(input_df) != len(predictions):
        raise ValueError(
            "The number of predictions must match the input records."
        )

    results = []

    for timestamp, demand in zip(
        input_df["timestamp"], predictions
    ):
        results.append(
            determine_grid_mode(timestamp, demand)
        )

    return pd.DataFrame(results)


if __name__ == "__main__":
    # Simple test cases for the switching rules.
    test_cases = [
        ("2026-10-24 12:00:00", 150),
        ("2026-10-24 12:00:00", 170),
        ("2026-10-24 19:00:00", 140),
        ("2026-10-24 15:00:00", 200),
    ]

    print("Smart Grid Controller Test\n")

    for timestamp, demand in test_cases:
        result = determine_grid_mode(timestamp, demand)
        print(result)
