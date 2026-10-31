import os
import warnings
from datetime import datetime

import features
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings('ignore')

DATA_DIR = '../data'

def load_and_process_file(filepath, label_val, name, max_rows=150000):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] Processing {name} (up to {max_rows} rows)...')
    
    parsed = []
    with open(filepath, 'r') as f:
        for i, line in enumerate(f):
            if i >= max_rows:
                break
            parts = line.strip().split(',')
            if len(parts) < 4:
                continue
            ts = parts[0]
            can_id = parts[1]
            dlc = parts[2]
            data_bytes = parts[3:-1]
            
            # Pad to 8 bytes
            data_bytes = data_bytes + ['00'] * (8 - len(data_bytes))
            data_bytes = data_bytes[:8]
            
            parsed.append([ts, can_id, dlc] + data_bytes + [parts[-1]])
            
    df = pd.DataFrame(parsed, columns=['Timestamp', 'CAN_ID', 'DLC', 'DATA0', 'DATA1', 'DATA2', 'DATA3', 'DATA4', 'DATA5', 'DATA6', 'DATA7', 'Flag'])
    
    df['Label'] = label_val
    df['Timestamp'] = pd.to_numeric(df['Timestamp'], errors='coerce')
    df = df.dropna(subset=['Timestamp'])
    df = df.sort_values(by='Timestamp').reset_index(drop=True)
    
    print(f'[{datetime.now().strftime("%H:%M:%S")}]   Computing features for {name} ({len(df)} rows) sequentially...')
    feat_df = features.extract_features(df)
    feat_df['Label'] = label_val
    
    # Split 80/20 temporally
    split_idx = int(len(feat_df) * 0.8)
    train_part = feat_df.iloc[:split_idx]
    test_part = feat_df.iloc[split_idx:]
    
    # Sample down to keep memory manageable (we want ~60k train and ~15k test per file)
    train_sample = train_part.sample(n=min(len(train_part), 60000), random_state=42)
    test_sample = test_part.sample(n=min(len(test_part), 15000), random_state=42)
    
    return train_sample, test_sample

print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Step 1-4: Loading, computing features independently per file, and temporal splitting...")
train_list = []
test_list = []

# Normal
tr, te = load_and_process_file(os.path.join(DATA_DIR, 'normal_run_data.txt'), 0, 'normal')
train_list.append(tr); test_list.append(te)
# DoS
tr, te = load_and_process_file(os.path.join(DATA_DIR, 'DoS_dataset.csv'), 1, 'DoS')
train_list.append(tr); test_list.append(te)
# Fuzzy
tr, te = load_and_process_file(os.path.join(DATA_DIR, 'Fuzzy_dataset.csv'), 2, 'Fuzzy')
train_list.append(tr); test_list.append(te)
# Spoofing (gear)
tr, te = load_and_process_file(os.path.join(DATA_DIR, 'gear_dataset.csv'), 3, 'Spoofing')
train_list.append(tr); test_list.append(te)

train_df = pd.concat(train_list, ignore_index=True)
test_df = pd.concat(test_list, ignore_index=True)

# Combine to apply top CAN IDs uniformly
full_df = pd.concat([train_df, test_df], ignore_index=True)
top_ids = full_df['CAN_ID_INT'].value_counts().nlargest(5).index.tolist()

print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Step 5: Applying Top 5 ID OHE (concatenation complete)...")
X_train_full, _ = features.apply_top_ids(train_df, top_ids)
y_train = train_df['Label']

X_test_full, _ = features.apply_top_ids(test_df, top_ids)
y_test = test_df['Label']

print(f"Final Train size: {len(X_train_full)} rows")
print(f"Final Test size: {len(X_test_full)} rows")

print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Training RandomForest with class_weight='balanced', n_jobs=-1...")
rf = RandomForestClassifier(class_weight='balanced', random_state=42, n_jobs=-1, max_depth=None, n_estimators=100)
rf.fit(X_train_full, y_train)

print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Evaluating on STRICT TEMPORAL TEST SET...")
y_pred = rf.predict(X_test_full)

print("\nStrict Temporal Split - Classification Report:")
print(classification_report(y_test, y_pred, digits=4))
print("Strict Temporal Split - Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))
