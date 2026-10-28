
import numpy as np

BATTERY_CAPACITY_KWH = 500.0
INITIAL_SOC_PERCENT = 80.0
MIN_SOC_PERCENT = 10.0
MAX_SOC_PERCENT = 100.0

CHARGE_POWER_KW = 50.0
DISCHARGE_POWER_KW = 50.0

CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95


def simulate_battery(forecast_df):
    """
    Simulate battery SOC across forecast intervals.

    Assumptions:
    - Battery capacity: 500 kWh.
    - Initial state of charge: 80%.
    - SOC limits: 10% to 100%.
    - Each forecast row represents one hour.
    - Renewable Storage Mode charges the battery.
    - Main Grid Mode discharges the battery.
    - This is a simulation, not real battery control.
    """

    required_columns = {"timestamp", "grid_mode"}

    if not required_columns.issubset(forecast_df.columns):
        raise ValueError(
            f"Forecast must contain columns: {required_columns}"
        )

    soc = INITIAL_SOC_PERCENT
    soc_values = []
    battery_power_values = []
    battery_actions = []

    for _, row in forecast_df.iterrows():
        if row["grid_mode"] == "Renewable Storage Mode":
            # Positive battery power means charging.
            available_capacity = (
                MAX_SOC_PERCENT - soc
            ) / 100 * BATTERY_CAPACITY_KWH

            energy_to_store = min(
                CHARGE_POWER_KW * CHARGE_EFFICIENCY,
                available_capacity,
            )

            soc += energy_to_store / BATTERY_CAPACITY_KWH * 100
            battery_power_values.append(CHARGE_POWER_KW)
            battery_actions.append("Charging")

        else:
            # Negative battery power means discharging.
            available_energy = (
                soc - MIN_SOC_PERCENT
            ) / 100 * BATTERY_CAPACITY_KWH

            energy_to_deliver = min(
                DISCHARGE_POWER_KW,
                available_energy * DISCHARGE_EFFICIENCY,
            )

            energy_removed = (
                energy_to_deliver / DISCHARGE_EFFICIENCY
            )

            soc -= energy_removed / BATTERY_CAPACITY_KWH * 100
            battery_power_values.append(-energy_to_deliver)
            battery_actions.append("Discharging")

        soc = float(
            np.clip(
                soc,
                MIN_SOC_PERCENT,
                MAX_SOC_PERCENT,
            )
        )

        soc_values.append(round(soc, 2))

    result = forecast_df.copy()
    result["battery_action"] = battery_actions
    result["battery_power_kw"] = np.round(
        battery_power_values, 2
    )
    result["battery_soc_percent"] = soc_values

    return result
