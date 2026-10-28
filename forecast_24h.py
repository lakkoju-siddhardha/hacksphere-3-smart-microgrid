
from datetime import datetime
import pandas as pd

from predict import predict
from grid_controller import build_forecast


def create_future_inputs(
    start_time=None,
    ambient_temp_c=28.0,
    humidity_pct=65.0,
    solar_irradiance_wm2=0.0,
):
    """
    Create 24 hourly input records.

    Weather values are manually supplied assumptions, not
    actual weather forecasts.
    """

    if start_time is None:
        start_time = pd.Timestamp.now().floor("h") + pd.Timedelta(hours=1)
    else:
        start_time = pd.Timestamp(start_time)

    timestamps = pd.date_range(
        start=start_time,
        periods=24,
        freq="h",
    )

    return pd.DataFrame({
        "timestamp": timestamps.strftime("%Y-%m-%d %H:%M:%S"),
        "ambient_temp_c": float(ambient_temp_c),
        "humidity_pct": float(humidity_pct),
        "solar_irradiance_wm2": float(solar_irradiance_wm2),
    })


def generate_24h_forecast(
    ambient_temp_c=28.0,
    humidity_pct=65.0,
    solar_irradiance_wm2=0.0,
):
    """Generate demand predictions and grid decisions for 24 hours."""

    future_inputs = create_future_inputs(
        ambient_temp_c=ambient_temp_c,
        humidity_pct=humidity_pct,
        solar_irradiance_wm2=solar_irradiance_wm2,
    )

    print("Generating 24-hour demand forecast...")

    predictions = predict(future_inputs)

    forecast_df = build_forecast(
        future_inputs,
        predictions,
    )

    forecast_df.to_csv("forecast_24h_results.csv", index=False)

    print("\n24-hour forecast completed!")
    print(forecast_df.to_string(index=False))

    print("\nGrid mode summary:")
    print(forecast_df["grid_mode"].value_counts().to_string())

    print(
        "\nCritical overload alerts:",
        int(forecast_df["critical_overload"].sum()),
    )

    print("\nSaved results to forecast_24h_results.csv")

    return forecast_df


if __name__ == "__main__":
    generate_24h_forecast()
