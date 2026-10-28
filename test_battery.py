
import pandas as pd

from battery_simulator import simulate_battery


sample_forecast = pd.DataFrame({
    "timestamp": [
        "2026-10-26 12:00:00",
        "2026-10-26 13:00:00",
        "2026-10-26 14:00:00",
        "2026-10-26 15:00:00",
    ],
    "grid_mode": [
        "Renewable Storage Mode",
        "Renewable Storage Mode",
        "Main Grid Mode",
        "Main Grid Mode",
    ],
})

result = simulate_battery(sample_forecast)

assert len(result) == len(sample_forecast)
assert result["battery_soc_percent"].between(10, 100).all()
assert result["battery_action"].notna().all()

print("Battery simulation tests passed!")
print(
    result[
        [
            "timestamp",
            "grid_mode",
            "battery_action",
            "battery_power_kw",
            "battery_soc_percent",
        ]
    ].to_string(index=False)
)
