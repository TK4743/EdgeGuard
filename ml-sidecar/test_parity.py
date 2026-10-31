import json
import os

import features
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, 'processed_data.csv')
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'model_config.json')
PARITY_FILE = os.path.join(SCRIPT_DIR, 'parity_test_data.json')


def test_feature_parity():
    """Verify that Python feature extraction reproduces parity test vectors."""
    if not os.path.exists(PARITY_FILE):
        if os.path.exists(DATA_FILE):
            generate_parity_data()
        else:
            print(f"Error: Neither {PARITY_FILE} nor {DATA_FILE} exists.")
            return False

    with open(PARITY_FILE, 'r') as f:
        test_cases = json.load(f)

    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    top_ids = config['top_5_can_ids']

    # Build DataFrame from raw test case messages
    records = []
    for tc in test_cases:
        raw = tc['raw']
        row = {
            'Timestamp': raw['Timestamp'],
            'CAN_ID': raw['CAN_ID'],
            'DLC': raw['DLC'],
            'Flag': raw['Flag'],
        }
        for i in range(8):
            row[f'DATA{i}'] = raw['DATA'][i]
        records.append(row)

    df = pd.DataFrame(records)
    feat_df = features.extract_features(df)
    X, _ = features.apply_top_ids(feat_df, top_ids)

    passed = 0
    total_evaluated = 0

    print(f"\nEvaluating parity on {len(test_cases)} sequential CAN frames (warmup: 80, evaluated: 20)...")
    for tc in test_cases:
        idx = tc['index']
        expected_features = tc['features']
        extracted_features = X.iloc[idx].values

        if idx >= 80:
            total_evaluated += 1
            max_diff = np.max(np.abs(extracted_features - expected_features))
            if max_diff <= 1e-4:
                passed += 1
            else:
                print(f"FAILED parity check at index {idx}: max_diff={max_diff}")

    print(f"Parity Test Result: {passed} / {total_evaluated} passed (diff <= 1e-4).")
    if passed == total_evaluated and total_evaluated == 20:
        print("SUCCESS: Python feature extraction verified with 100% parity!")
        return True
    else:
        print("FAILURE: Parity check did not reach 100%.")
        return False


def generate_parity_data():
    if not os.path.exists(DATA_FILE):
        print(f"Cannot generate parity data: {DATA_FILE} does not exist.")
        return

    df = pd.read_csv(DATA_FILE)
    df_sample = df.iloc[5000:5100].copy().reset_index(drop=True)
    features_df = features.extract_features(df_sample)

    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    top_ids = config['top_5_can_ids']

    features_df, _ = features.apply_top_ids(features_df, top_ids)

    test_cases = []
    for idx in range(len(df_sample)):
        raw_row = df_sample.iloc[idx]
        feat_row = features_df.iloc[idx]
        data_bytes = [str(raw_row[f'DATA{i}']) for i in range(8)]
        test_case = {
            'index': int(idx),
            'raw': {
                'Timestamp': float(raw_row['Timestamp']),
                'CAN_ID': str(raw_row['CAN_ID']),
                'DLC': int(raw_row['DLC']),
                'DATA': data_bytes,
                'Flag': str(raw_row['Flag']),
            },
            'features': feat_row.values.tolist(),
        }
        test_cases.append(test_case)

    with open(PARITY_FILE, 'w') as f:
        json.dump(test_cases, f, indent=4)

    print(f"Exported 100 sequential test cases to {PARITY_FILE}")


if __name__ == '__main__':
    test_feature_parity()
