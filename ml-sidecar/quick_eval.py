import os
import sys
import warnings

import features
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings('ignore')

if not os.path.exists('processed_data.csv'):
    print('processed_data.csv not found. Please run load_data.py first.')
    sys.exit(0)

print('Loading data...')
df = pd.read_csv('processed_data.csv')
features_df = features.extract_features(df)
top_ids = features_df['CAN_ID_INT'].value_counts().nlargest(5).index.tolist()
X, _ = features.apply_top_ids(features_df, top_ids)
y = df['Label']

print('Splitting data...')
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print('\nApproach 1: class_weight=\'balanced\'')
rf_bal = RandomForestClassifier(class_weight='balanced', random_state=42, n_jobs=-1, max_depth=None, n_estimators=100)
rf_bal.fit(X_train, y_train)
y_pred_bal = rf_bal.predict(X_test)
print(classification_report(y_test, y_pred_bal, digits=4))

print('\nApproach 2: SMOTE')
smote = SMOTE(random_state=42)
X_train_sm, y_train_sm = smote.fit_resample(X_train, y_train)
rf_smote = RandomForestClassifier(random_state=42, n_jobs=-1, max_depth=None, n_estimators=100)
rf_smote.fit(X_train_sm, y_train_sm)
y_pred_sm = rf_smote.predict(X_test)
print(classification_report(y_test, y_pred_sm, digits=4))
