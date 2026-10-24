
import pandas as pd
import numpy as np
from pathlib import Path

# Locate the datasets in the project folder
BASE_DIR = Path(__file__).parent

train_path = BASE_DIR / "train_telemetry.csv"
test_path = BASE_DIR / "sample_test_input.csv"

# Load datasets
train = pd.read_csv(train_path)
test = pd.read_csv(test_path)

print("=" * 60)
print("HACKSPHERE 3.0 - DATASET ANALYSIS")
print("=" * 60)

print("\n1. DATASET SHAPES")
print("Training:", train.shape)
print("Testing :", test.shape)

print("\n2. TRAINING COLUMNS")
print(train.columns.tolist())

print("\n3. FIRST 5 TRAINING ROWS")
print(train.head().to_string(index=False))

print("\n4. FIRST 5 TEST ROWS")
print(test.head().to_string(index=False))

print("\n5. MISSING VALUES IN TRAINING DATA")
print(train.isnull().sum())

print("\n6. DUPLICATE ROWS")
print("Training:", train.duplicated().sum())
print("Testing :", test.duplicated().sum())

print("\n7. NUMERICAL SUMMARY")
print(train.describe().round(2).to_string())

print("\n8. TIMESTAMP INFORMATION")
for name, df in [("Training", train), ("Testing", test)]:
    timestamps = pd.to_datetime(df["timestamp"], errors="coerce")
    print(f"\n{name}:")
    print("Invalid timestamps:", timestamps.isna().sum())
    print("Earliest:", timestamps.min())
    print("Latest  :", timestamps.max())

print("\n9. TEST DATA COLUMN CHECK")
required = {
    "timestamp",
    "ambient_temp_c",
    "humidity_pct",
    "solar_irradiance_wm2",
}

print("Missing required columns:", required - set(test.columns))

print("\n10. TARGET DISTRIBUTION")
target = train["target_demand_kw"]
print("Minimum demand:", round(target.min(), 2), "kW")
print("Maximum demand:", round(target.max(), 2), "kW")
print("Average demand:", round(target.mean(), 2), "kW")
print("Median demand :", round(target.median(), 2), "kW")

print("\nAnalysis complete!")

