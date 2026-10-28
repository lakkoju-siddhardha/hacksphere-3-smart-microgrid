from zoho_auth import get_access_token
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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
REQUEST_TIMEOUT = (10, 90)


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
        "Authorization": f"Zoho-oauthtoken {get_access_token()}",
        "CATALYST-ORG": CATALYST_ORG,
        "Environment": CATALYST_ENVIRONMENT,
        "Content-Type": "application/json",

    }

    all_predictions = []
    total = len(input_df)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    
    retry_strategy = Retry(
    total=3,
    connect=3,
    read=2,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"],
    respect_retry_after_header=True,
)

    adapter = HTTPAdapter(max_retries=retry_strategy)

    with requests.Session() as session:
        session.mount("https://", adapter)

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
                    "Check endpoint configuration, credentials, "
                    "or network connectivity."
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
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate energy demand predictions using Zoho QuickML."
    )
    parser.add_argument(
        "--input",
        default="sample_test_input.csv",
        help="Path to the input CSV file",
    )
    parser.add_argument(
        "--output",
        default="predictions.csv",
        help="Path to save the prediction CSV file",
    )

    args = parser.parse_args()

    print("Loading input data...")

    input_df = pd.read_csv(args.input)

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in input_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Input CSV is missing required columns: "
            f"{', '.join(missing_columns)}"
        )

    print(f"Loaded {len(input_df)} records.")
    print("Connecting to Zoho QuickML...")

    predictions = predict(input_df)

    if len(predictions) != len(input_df):
        raise RuntimeError(
            f"Expected {len(input_df)} predictions, "
            f"but received {len(predictions)}."
        )

    if not np.isfinite(predictions).all():
        raise RuntimeError("Predictions contain invalid numeric values.")

    output_df = pd.DataFrame({
        "timestamp": input_df["timestamp"].values,
        "target_demand_kw": predictions,
    })

    output_df.to_csv(
        args.output,
        index=False,
        float_format="%.2f",
    )

    print("\nQuickML prediction completed successfully!")
    print(f"Total records: {len(output_df)}")
    print(f"Output file: {os.path.abspath(args.output)}")
    print(f"Output columns: {list(output_df.columns)}")
    print("\nFirst 5 predictions:")

    print(output_df.head().to_string(index=False))

