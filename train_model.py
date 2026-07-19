"""
train_model.py
--------------
Train the irrigation ML models from the dataset.
Run this once. Models are saved as .pkl files used by server.py.

Usage:
    python train_model.py
"""

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_absolute_error, accuracy_score

# ── Load Dataset ──────────────────────────────────────────────────────────────
DATASET_PATH = 'irrigation_ml_dataset.csv'

print("="*55)
print("  Smart Irrigation ML - Model Training")
print("="*55)

df = pd.read_csv(DATASET_PATH)
print(f"Dataset loaded: {len(df)} rows")
print(f"Motor ON: {df['motor_state'].sum()}  |  Motor OFF: {(df['motor_state']==0).sum()}")

# ── Features & Targets ────────────────────────────────────────────────────────
FEATURES = ['temperature_c', 'humidity_pct', 'soil_moisture_pct']
X        = df[FEATURES]
y_class  = df['motor_state']            # Classification: 0 or 1
y_reg    = df['motor_on_duration_min']  # Regression: minutes

# ── Train/Test Split ──────────────────────────────────────────────────────────
X_train, X_test, yc_train, yc_test, yr_train, yr_test = train_test_split(
    X, y_class, y_reg, test_size=0.2, random_state=42, stratify=y_class)

print(f"\nTrain: {len(X_train)} rows  |  Test: {len(X_test)} rows")

# ── Model 1: Motor State Classifier (ON / OFF) ───────────────────────────────
print("\n--- Training Motor State Classifier ---")
clf = RandomForestClassifier(
    n_estimators=150,
    max_depth=10,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1
)
clf.fit(X_train, yc_train)
yc_pred = clf.predict(X_test)
acc = accuracy_score(yc_test, yc_pred)
print(f"Accuracy: {acc*100:.2f}%")
print(classification_report(yc_test, yc_pred, target_names=['OFF','ON']))

# Feature importance
fi = pd.Series(clf.feature_importances_, index=FEATURES).sort_values(ascending=False)
print("Feature Importance:")
for feat, imp in fi.items():
    print(f"  {feat:25s}: {imp*100:.1f}%")

# ── Model 2: Duration Regressor (minutes motor runs) ─────────────────────────
print("\n--- Training Duration Regressor ---")
# Train only on cases where motor IS on (duration > 0)
mask_train = yr_train > 0
mask_test  = yr_test > 0

reg = RandomForestRegressor(
    n_estimators=150,
    max_depth=10,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1
)
reg.fit(X_train[mask_train], yr_train[mask_train])
yr_pred = reg.predict(X_test[mask_test])
mae = mean_absolute_error(yr_test[mask_test], yr_pred)
print(f"Mean Absolute Error: {mae:.2f} minutes")
print(f"Training rows used: {mask_train.sum()}")

# ── Save Models ───────────────────────────────────────────────────────────────
with open('motor_classifier.pkl', 'wb') as f:
    pickle.dump(clf, f)
with open('duration_regressor.pkl', 'wb') as f:
    pickle.dump(reg, f)

print("\n✅ Models saved:")
print("   motor_classifier.pkl")
print("   duration_regressor.pkl")

# ── Quick Sanity Tests ────────────────────────────────────────────────────────
print("\n--- Sample Predictions ---")
tests = [
    {'temperature_c': 32, 'humidity_pct': 60, 'soil_moisture_pct': 15, 'label': 'Hot & Very Dry'},
    {'temperature_c': 25, 'humidity_pct': 75, 'soil_moisture_pct': 30, 'label': 'Normal & Dry'},
    {'temperature_c': 22, 'humidity_pct': 85, 'soil_moisture_pct': 70, 'label': 'Cool & Wet'},
    {'temperature_c': 30, 'humidity_pct': 95, 'soil_moisture_pct': 80, 'label': 'Humid & Wet'},
]

for t in tests:
    label = t.pop('label')
    sample = pd.DataFrame([t])
    state = int(clf.predict(sample)[0])
    dur   = round(float(reg.predict(sample)[0]), 1) if state == 1 else 0.0
    dur   = max(1.0, dur) if state == 1 else 0.0
    print(f"  {label:22s} → Motor {'ON ':3s} {dur:.0f} min" if state else f"  {label:22s} → Motor OFF")

print("\n✅ Training complete! Run server.py to start the ML server.")
