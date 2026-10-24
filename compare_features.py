
import numpy as np
import pandas as pd

from pathlib import Path
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

BASE_DIR = Path(__file__).parent
df = pd.read_csv(BASE_DIR / "train_telemetry.csv")

df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
df = df.sort_values("timestamp").reset_index(drop=True)

weather_features = [
    "ambient_temp_c",
    "humidity_pct",
    "solar_irradiance_wm2",
]

# Candidate 1: weather features only
X_weather = df[weather_features].copy()

# Candidate 2: weather + calendar features
X_calendar = X_weather.copy()

hour = df["timestamp"].dt.hour
day_of_week = df["timestamp"].dt.day_of_week
month = df["timestamp"].dt.month

X_calendar["hour"] = hour
X_calendar["day_of_week"] = day_of_week
X_calendar["month"] = month

# Candidate 3: weather + cyclical time features
X_cyclical = X_weather.copy()

X_cyclical["hour_sin"] = np.sin(2 * np.pi * hour / 24)
X_cyclical["hour_cos"] = np.cos(2 * np.pi * hour / 24)

X_cyclical["weekday_sin"] = np.sin(2 * np.pi * day_of_week / 7)
X_cyclical["weekday_cos"] = np.cos(2 * np.pi * day_of_week / 7)

X_cyclical["month_sin"] = np.sin(2 * np.pi * (month - 1) / 12)
X_cyclical["month_cos"] = np.cos(2 * np.pi * (month - 1) / 12)

y = df["target_demand_kw"]

split = int(len(df) * 0.8)

y_train = y.iloc[:split]
y_val = y.iloc[split:]

feature_sets = {
    "Weather only": X_weather,
    "Weather + calendar": X_calendar,
    "Weather + cyclical time": X_cyclical,
}

results = []

for name, X in feature_sets.items():
    model = ExtraTreesRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X.iloc[:split], y_train)
    predictions = model.predict(X.iloc[split:])

    results.append({
        "Features": name,
        "RMSE_kW": np.sqrt(mean_squared_error(y_val, predictions)),
        "MAE_kW": mean_absolute_error(y_val, predictions),
        "R2": r2_score(y_val, predictions),
    })

results_df = pd.DataFrame(results).sort_values("RMSE_kW")

print("\nHACKSPHERE 3.0 - FEATURE COMPARISON")
print(results_df.to_string(
    index=False,
    float_format=lambda value: f"{value:.4f}"
))

print("\nLower RMSE is better.")

