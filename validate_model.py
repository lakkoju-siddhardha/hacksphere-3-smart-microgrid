
import numpy as np
import pandas as pd

from pathlib import Path
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error

BASE_DIR = Path(__file__).parent

df = pd.read_csv(BASE_DIR / "train_telemetry.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")

df = df.sort_values("timestamp").reset_index(drop=True)

weather = [
    "ambient_temp_c",
    "humidity_pct",
    "solar_irradiance_wm2",
]

X_weather = df[weather].copy()

hour = df["timestamp"].dt.hour
day = df["timestamp"].dt.day_of_week
month = df["timestamp"].dt.month

X_calendar = X_weather.copy()

X_calendar["hour"] = hour
X_calendar["day_of_week"] = day
X_calendar["month"] = month

y = df["target_demand_kw"]

# Expanding chronological validation windows.
# Every validation window occurs strictly after its training window.
splits = [
    (2000, 2400),
    (2400, 2800),
    (2800, 3200),
    (3200, 3600),
    (3600, 4000),
]

results = []

for split_number, (train_end, val_end) in enumerate(splits, start=1):
    X_train_weather = X_weather.iloc[:train_end]
    X_val_weather = X_weather.iloc[train_end:val_end]

    X_train_calendar = X_calendar.iloc[:train_end]
    X_val_calendar = X_calendar.iloc[train_end:val_end]

    y_train = y.iloc[:train_end]
    y_val = y.iloc[train_end:val_end]

    for feature_name, X_train, X_val in [
        (
            "Weather only",
            X_train_weather,
            X_val_weather,
        ),
        (
            "Weather + calendar",
            X_train_calendar,
            X_val_calendar,
        ),
    ]:
        model = ExtraTreesRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

        model.fit(X_train, y_train)
        predictions = model.predict(X_val)

        results.append({
            "Window": split_number,
            "Features": feature_name,
            "Training_rows": train_end,
            "Validation_rows": val_end - train_end,
            "RMSE_kW": np.sqrt(
                mean_squared_error(y_val, predictions)
            ),
            "MAE_kW": mean_absolute_error(
                y_val, predictions
            ),
        })

results_df = pd.DataFrame(results)

print("\nHACKSPHERE 3.0 - CHRONOLOGICAL VALIDATION\n")

print(
    results_df.to_string(
        index=False,
        float_format=lambda value: f"{value:.4f}",
    )
)

print("\nAVERAGE VALIDATION ERRORS\n")

summary = (
    results_df
    .groupby("Features")[["RMSE_kW", "MAE_kW"]]
    .mean()
    .sort_values("RMSE_kW")
)

print(summary.to_string(float_format=lambda value: f"{value:.4f}"))

print("\nLower RMSE is better.")
