
import os
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

QUICKML_ENDPOINT_URL = os.getenv("QUICKML_ENDPOINT_URL")
QUICKML_ENDPOINT_KEY = os.getenv("QUICKML_ENDPOINT_KEY")
ZOHO_ACCESS_TOKEN = os.getenv("ZOHO_ACCESS_TOKEN")
CATALYST_ORG = os.getenv("CATALYST_ORG")
CATALYST_ENVIRONMENT = os.getenv(
    "CATALYST_ENVIRONMENT", "Development"
)

REQUIRED_COLUMNS = [
    "timestamp",
    "ambient_temp_c",
    "humidity_pct",
    "solar_irradiance_wm2",
]

BATCH_SIZE = 50
REQUEST_TIMEOUT = 30


def predict(input_df: pd.DataFrame) -> np.ndarray:
    """Predict demand using the published Zoho QuickML endpoint."""

    if input_df.empty:
        return np.array([], dtype=float)

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in input_df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Missing columns: {', '.join(missing_columns)}"
        )

    config = {
        "QUICKML_ENDPOINT_URL": QUICKML_ENDPOINT_URL,
        "QUICKML_ENDPOINT_KEY": QUICKML_ENDPOINT_KEY,
        "ZOHO_ACCESS_TOKEN": ZOHO_ACCESS_TOKEN,
        "CATALYST_ORG": CATALYST_ORG,
    }

    missing_config = [
        key for key, value in config.items() if not value
    ]
    if missing_config:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing_config)
        )

    headers = {
        "X-QUICKML-ENDPOINT-KEY": QUICKML_ENDPOINT_KEY,
        "Authorization": f"Zoho-oauthtoken {ZOHO_ACCESS_TOKEN}",
        "CATALYST-ORG": CATALYST_ORG,
        "Environment": CATALYST_ENVIRONMENT,
        "Content-Type": "application/json",
    }

    all_predictions = []
    total = len(input_df)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    with requests.Session() as session:
        for start in range(0, total, BATCH_SIZE):
            batch = input_df.iloc[start:start + BATCH_SIZE]

            records = batch[REQUIRED_COLUMNS].copy()
            records["timestamp"] = records["timestamp"].astype(str)

            # Convert NumPy values to native Python values for JSON.
            records = records.astype(object).where(
                pd.notna(records), None
            )
            payload = {"data": records.to_dict(orient="records")}

            batch_number = start // BATCH_SIZE + 1

            try:
                response = session.post(
                    QUICKML_ENDPOINT_URL,
                    headers=headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                result = response.json()

            except requests.RequestException as exc:
                status = (
                    exc.response.status_code
                    if exc.response is not None
                    else "no HTTP response"
                )
                raise RuntimeError(
                    f"QuickML request failed for batch "
                    f"{batch_number}/{total_batches}; "
                    f"HTTP status: {status}. "
                    "Check endpoint configuration and credentials."
                ) from exc

            values = result.get("result")

            if (
                result.get("status") != "success"
                or not isinstance(values, list)
                or len(values) != len(batch)
            ):
                raise RuntimeError(
                    f"Unexpected QuickML response for batch "
                    f"{batch_number}/{total_batches}. "
                    f"Expected {len(batch)} predictions; "
                    "check the endpoint response format."
                )

            try:
                batch_predictions = np.asarray(values, dtype=float)
            except (TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"QuickML returned non-numeric predictions "
                    f"for batch {batch_number}."
                ) from exc

            if not np.isfinite(batch_predictions).all():
                raise RuntimeError(
                    f"QuickML returned invalid numeric values "
                    f"for batch {batch_number}."
                )

            all_predictions.extend(batch_predictions.tolist())

            print(
                f"Completed batch {batch_number}/{total_batches} "
                f"({len(all_predictions)}/{total} records)"
            )

    return np.asarray(all_predictions, dtype=float)


if __name__ == "__main__":
    print("Testing connection to Zoho QuickML...")

    sample_df = pd.read_csv("sample_test_input.csv")
    predictions = predict(sample_df)

    print("\nQuickML prediction completed successfully!")
    print(f"Total records: {len(predictions)}")
    print("First 5 predictions:")

    for value in predictions[:5]:
        print(f"{value:.2f} kW")
