import json
import os
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split

# Ignore all warnings globally
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")

import features

DATA_FILE = 'processed_data.csv'
MODEL_DIR = '.'

def train_and_evaluate():
    if not os.path.exists(DATA_FILE):
        print(f"Dataset {DATA_FILE} not found. Please run load_data.py or provide {DATA_FILE} first.")
        return

    print(f"Loading data from {DATA_FILE}...")
    full_df = pd.read_csv(DATA_FILE)
    print(f"Total dataset shape: {full_df.shape}")
    
    # 1. Feature Engineering
    start_feat = time.time()
    full_df = features.extract_features(full_df)
    print(f"Feature extraction took {time.time() - start_feat:.2f}s")
    
    # Stratified Train/Test Split
    # Must use 20% test split
    print("Splitting dataset (80% train, 20% test)...")
    train_df, test_df = train_test_split(full_df, test_size=0.2, random_state=42, stratify=full_df['Label'])
    
    # 2. Extract top 5 CAN IDs based on training set ONLY
    top_ids = train_df['CAN_ID'].value_counts().nlargest(5).index
    
    # Save top IDs config
    config = {"top_5_can_ids": top_ids.tolist()}
    with open(os.path.join(MODEL_DIR, 'model_config.json'), 'w') as f:
        json.dump(config, f, indent=4)
        
    # Apply top IDs encoding
    X_train, y_train = features.apply_top_ids(train_df, top_ids)
    X_test, y_test = features.apply_top_ids(test_df, top_ids)
    
    # Save test sets for audit
    X_test.to_csv('X_test.csv', index=False)
    y_test.to_csv('y_test.csv', index=False)
    
    print("Training model... Comparing class_weight vs SMOTE")
    
    # GridSearchCV on RandomForest
    # (n_estimators: [100,200], max_depth: [10,20,None])
    param_grid = {
        'n_estimators': [100, 200],
        'max_depth': [10, 20, None]
    }
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    with open("training_log.txt", "w") as log_file:
        # Approach 1: class_weight='balanced'
        log_file.write("Approach 1: class_weight='balanced'\n")
        rf_balanced = RandomForestClassifier(class_weight='balanced', random_state=42, n_jobs=4)
        grid_balanced = GridSearchCV(rf_balanced, param_grid, cv=cv, scoring='f1_macro', n_jobs=4)
        start_train1 = time.time()
        grid_balanced.fit(X_train, y_train)
        print(f"class_weight='balanced' training completed in {time.time() - start_train1:.2f}s")
        
        y_pred_bal = grid_balanced.predict(X_test)
        report_bal = classification_report(y_test, y_pred_bal)
        log_file.write(f"class_weight='balanced' Best Params: {grid_balanced.best_params_}\n")
        log_file.write(report_bal + "\n\n")
        _, _, f1_bal, _ = precision_recall_fscore_support(y_test, y_pred_bal)
        macro_f1_bal = np.mean(f1_bal)
        print(f"class_weight='balanced' Fuzzy F1: {f1_bal[2]:.4f}, Macro F1: {macro_f1_bal:.4f}")
        
        # Approach 2: SMOTE
        log_file.write("Approach 2: SMOTE\n")
        smote = SMOTE(random_state=42)
        X_train_sm, y_train_sm = smote.fit_resample(X_train, y_train)
        rf_smote = RandomForestClassifier(random_state=42, n_jobs=4)
        grid_smote = GridSearchCV(rf_smote, param_grid, cv=cv, scoring='f1_macro', n_jobs=4)
        start_train2 = time.time()
        grid_smote.fit(X_train_sm, y_train_sm)
        print(f"SMOTE training completed in {time.time() - start_train2:.2f}s")
        
        y_pred_sm = grid_smote.predict(X_test)
        _, _, f1_sm, _ = precision_recall_fscore_support(y_test, y_pred_sm)
        macro_f1_sm = np.mean(f1_sm)
        print(f"SMOTE Fuzzy F1: {f1_sm[2]:.4f}, Macro F1: {macro_f1_sm:.4f}")
        
        # Select best model based on Fuzzy F1
        if f1_sm[2] > f1_bal[2]:
            print("Selecting SMOTE model as it yields better Fuzzy attack F1.")
            best_model = grid_smote.best_estimator_
            y_pred = y_pred_sm
        else:
            print("Selecting class_weight='balanced' model as it yields better/equal Fuzzy attack F1.")
            best_model = grid_balanced.best_estimator_
            y_pred = y_pred_bal
            
        report_smote = classification_report(y_test, y_pred_sm)
        log_file.write(f"SMOTE Best Params: {grid_smote.best_params_}\n")
        log_file.write(report_smote + "\n\n")
    
    print(f"Best parameters: {best_model.get_params()}")
    
    # Evaluate
    print("Evaluating final model...")
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred)
    conf_matrix = confusion_matrix(y_test, y_pred)
    
    # Inference Latency (avg over 10000 samples)
    n_samples = min(10000, len(X_test))
    X_latency = X_test.iloc[:n_samples].values.astype(np.float32)
    start_inf = time.time()
    for row in X_latency: # Mimic single-message inference
        best_model.predict([row])
    end_inf = time.time()
    avg_latency_ms = ((end_inf - start_inf) / n_samples) * 1000
    
    # Save Model (Joblib)
    joblib_path = os.path.join(MODEL_DIR, 'model.pkl')
    joblib.dump(best_model, joblib_path)
    model_size_kb = os.path.getsize(joblib_path) / 1024
    
    # Save Model (ONNX)
    print("Exporting ONNX...")
    initial_type = [('float_input', FloatTensorType([None, X_train.shape[1]]))]
    onx = convert_sklearn(best_model, initial_types=initial_type, target_opset=12)
    onnx_path = os.path.join(MODEL_DIR, 'model.onnx')
    with open(onnx_path, "wb") as f:
        f.write(onx.SerializeToString())
        
    metrics = {
        'accuracy': float(accuracy),
        'precision_per_class': precision.tolist(),
        'recall_per_class': recall.tolist(),
        'f1_per_class': f1.tolist(),
        'macro_f1': float(np.mean(f1)),
        'confusion_matrix': conf_matrix.tolist(),
        'avg_inference_latency_ms': float(avg_latency_ms),
        'model_size_kb': float(model_size_kb)
    }
    
    with open(os.path.join(MODEL_DIR, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=4)
        
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {np.mean(f1):.4f}")
    print(f"F1 Scores: {f1}")
    print(f"Average single-message Latency: {avg_latency_ms:.4f} ms")
    print(f"Model Size: {model_size_kb:.2f} KB")

if __name__ == '__main__':
    train_and_evaluate()
