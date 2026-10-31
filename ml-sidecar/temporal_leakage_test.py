import os
import sys
import warnings

import features
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings('ignore')

if not os.path.exists('processed_data.csv'):
    print('processed_data.csv not found. Please run load_data.py first.')
    sys.exit(0)

print('Loading data...')
df = pd.read_csv('processed_data.csv')

# Ensure chronological order for time-based split
df = df.sort_values(by='Timestamp').reset_index(drop=True)

print('Extracting features...')
features_df = features.extract_features(df)
top_ids = features_df['CAN_ID_INT'].value_counts().nlargest(5).index.tolist()
X, _ = features.apply_top_ids(features_df, top_ids)
y = df['Label']

# --- EXPERIMENT 1: RANDOM SPLIT ---
print('\n=======================================')
print('EXPERIMENT 1: RANDOM SPLIT (Stratified)')
print('=======================================')
X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

rf_random = RandomForestClassifier(class_weight='balanced', random_state=42, n_jobs=-1, max_depth=None, n_estimators=100)
rf_random.fit(X_train_r, y_train_r)
y_pred_r = rf_random.predict(X_test_r)

print("\nRandom Split - Classification Report:")
print(classification_report(y_test_r, y_pred_r, digits=4))
print("Random Split - Confusion Matrix:")
print(confusion_matrix(y_test_r, y_pred_r))


# --- EXPERIMENT 2: TIME-BASED SPLIT ---
print('\n=======================================')
print('EXPERIMENT 2: TIME-BASED SPLIT (Chronological)')
print('=======================================')
split_idx = int(len(X) * 0.8)
X_train_t, X_test_t = X.iloc[:split_idx], X.iloc[split_idx:]
y_train_t, y_test_t = y.iloc[:split_idx], y.iloc[split_idx:]

# Since it's time-based, classes might be imbalanced in train vs test. 
# We'll use the same algorithm (class_weight='balanced').
rf_time = RandomForestClassifier(class_weight='balanced', random_state=42, n_jobs=-1, max_depth=None, n_estimators=100)
rf_time.fit(X_train_t, y_train_t)
y_pred_t = rf_time.predict(X_test_t)

print("\nTime-Based Split - Classification Report:")
print(classification_report(y_test_t, y_pred_t, digits=4))
print("Time-Based Split - Confusion Matrix:")
print(confusion_matrix(y_test_t, y_pred_t))
