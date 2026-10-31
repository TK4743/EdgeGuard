import json
import os

import features
import joblib
import numpy as np
import onnxruntime as rt
import pandas as pd

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(MODEL_DIR, 'processed_data.csv')
PARITY_FILE = os.path.join(MODEL_DIR, 'parity_test_data.json')

def verify_models():
    print("Loading data for verification...")
    if os.path.exists(DATA_FILE):
        full_df = pd.read_csv(DATA_FILE).head(1000).copy()
        full_df = features.extract_features(full_df)
    elif os.path.exists(PARITY_FILE):
        with open(PARITY_FILE, 'r') as f:
            test_cases = json.load(f)
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
        full_df = pd.DataFrame(records)
        full_df = features.extract_features(full_df)
    else:
        print("Neither processed_data.csv nor parity_test_data.json found.")
        return
    
    with open(os.path.join(MODEL_DIR, 'model_config.json'), 'r') as f:
        config = json.load(f)
    top_ids = config['top_5_can_ids']
    
    X, _y = features.apply_top_ids(full_df, top_ids)
    
    X_batch = X.values.astype(np.float32)
    
    # Sklearn predictions
    print("Running sklearn predictions...")
    pkl_model = joblib.load(os.path.join(MODEL_DIR, 'model.pkl'))
    pkl_preds = pkl_model.predict(X_batch)
    
    # ONNX predictions
    print("Running ONNX predictions...")
    sess = rt.InferenceSession(os.path.join(MODEL_DIR, 'model.onnx'), providers=['CPUExecutionProvider'])
    input_name = sess.get_inputs()[0].name
    label_name = sess.get_outputs()[0].name
    
    onnx_preds = sess.run([label_name], {input_name: X_batch})[0]
    
    # Compare
    matches = (pkl_preds == onnx_preds)
    accuracy = np.sum(matches) / len(matches)
    
    print(f"Match accuracy between ONNX and Sklearn on {len(matches)} rows: {accuracy * 100:.2f}%")
    if accuracy == 1.0:
        print("SUCCESS: ONNX model predictions perfectly match Sklearn model.")
    else:
        print("WARNING: Mismatch detected between models.")
        
    # Also test shape matches expected Java 13 features
    if X_batch.shape[1] != 13:
        print(f"WARNING: Expected 13 features for Java parity, got {X_batch.shape[1]}")
    else:
        print("SUCCESS: 13 features confirmed for Java parity.")

if __name__ == '__main__':
    verify_models()
