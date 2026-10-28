from battery_simulator import simulate_battery
import pandas as pd

from predict import predict
from grid_controller import build_forecast


def generate_forecast(input_csv="sample_test_input.csv"):
    """
    Generate demand predictions and determine grid operating modes.

    Note: The default CSV contains historical test records.
    Use future timestamps and forecast weather inputs for a real
    next-24-hour forecast.
    """

    print("Loading input data...")
    input_df = pd.read_csv(input_csv)

    print(f"Loaded {len(input_df)} records.")

    print("\nRequesting predictions from Zoho QuickML...")
    predictions = predict(input_df)

    print("\nApplying smart grid rules...") 
    forecast_df = build_forecast(input_df, predictions)

    print("\nSimulating battery state of charge...")
    forecast_df = simulate_battery(forecast_df)

    output_file = "forecast_results.csv"
    forecast_df.to_csv(output_file, index=False)

    print(f"\nForecast results saved to {output_file}")

    print("\nFirst 10 results:")
    print(forecast_df.head(10).to_string(index=False))

    print("\nGrid mode summary:")
    print(forecast_df["grid_mode"].value_counts().to_string())

    alerts = forecast_df[forecast_df["critical_overload"]]

    print(f"\nCritical overload alerts: {len(alerts)}")

    if not alerts.empty:
        print(alerts.to_string(index=False))

    return forecast_df


if __name__ == "__main__":
    generate_forecast()
