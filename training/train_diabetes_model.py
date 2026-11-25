"""
Module 2B — train_diabetes_model.py
Train a RandomForestClassifier on the diabetes prediction dataset.

Dataset : data/diabetes_prediction_dataset.csv  (comma-separated, 100,000 rows)
Target  : diabetes (0/1, ~8.5% positive — imbalanced)
Output  : models/diabetes_model_unweighted.pkl (or diabetes_model.pkl with --balanced)

Preprocessing steps (per spec):
  1. Drop exact duplicate rows (~3,854) BEFORE train/test split
  2. One-hot encode 'gender' (Female / Male / Other — 3 categories)
  3. One-hot encode 'smoking_history' (6 categories, 'No Info' kept as-is)
  4. Age is already in years — no conversion needed
    5. Optionally use class_weight='balanced' for the active model
"""

import argparse
import os
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    classification_report,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

# Suppress the NumPy 1.x/2.x compatibility warnings from numexpr/bottleneck
warnings.filterwarnings("ignore", message=".*NumPy 1.x.*")
warnings.filterwarnings("ignore", category=UserWarning)

# ─────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "diabetes_prediction_dataset.csv")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "diabetes_model_unweighted.pkl")

TARGET = "diabetes"
RANDOM_STATE = 42


def load_and_preprocess(path: str) -> tuple[pd.DataFrame, list[str]]:
    """Load the diabetes dataset and apply all required cleaning/encoding.

    Steps:
        1. Read CSV.
        2. Drop exact duplicate rows.
        3. One-hot encode 'gender' (3 categories).
        4. One-hot encode 'smoking_history' (6 categories incl. 'No Info').

    Returns:
        (cleaned DataFrame, list of final feature column names)
    """
    print("Loading dataset from:", path)
    df = pd.read_csv(path)
    n_original = len(df)
    print(f"  Raw rows: {n_original:,}")

    # --- Step 1: drop exact duplicates ---
    n_dups = df.duplicated().sum()
    df = df.drop_duplicates().reset_index(drop=True)
    print(f"  Dropped {n_dups:,} exact duplicate rows")
    print(f"  Rows after dedup: {len(df):,}")

    # --- Step 2: one-hot encode 'gender' ---
    # drop_first=False → keep all 3 categories (Female, Male, Other)
    gender_dummies = pd.get_dummies(df["gender"], prefix="gender", dtype=int)
    print(f"  Gender categories: {sorted(df['gender'].unique())}")

    # --- Step 3: one-hot encode 'smoking_history' ---
    # 'No Info' is kept as its own valid category (not imputed/dropped)
    smoking_dummies = pd.get_dummies(
        df["smoking_history"], prefix="smoking", dtype=int,
    )
    print(f"  Smoking categories: {sorted(df['smoking_history'].unique())}")

    # Build final DataFrame
    df = pd.concat([df, gender_dummies, smoking_dummies], axis=1)
    df = df.drop(columns=["gender", "smoking_history"])

    # Identify feature columns (everything except target)
    feature_cols = [c for c in df.columns if c != TARGET]
    print(f"  Total features: {len(feature_cols)}")
    print(f"  Feature list: {feature_cols}")

    # Class distribution
    pos_rate = df[TARGET].mean()
    print(f"  Positive class rate: {pos_rate:.3f} ({pos_rate*100:.1f}%)")

    return df, feature_cols


def train_model(df: pd.DataFrame, feature_cols: list[str], balanced: bool = False) -> None:
    """Train and evaluate a RandomForest; save the candidate separately by default."""

    X = df[feature_cols]
    y = df[TARGET]

    # 80/20 stratified split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE,
    )
    print(f"\nTrain set: {len(X_train):,} | Test set: {len(X_test):,}")
    print(f"Positive-class rate  train={y_train.mean():.3f}  test={y_test.mean():.3f}")

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=10,
        class_weight="balanced" if balanced else None,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    print(f"\nTraining RandomForestClassifier (balanced={balanced}) …")
    clf.fit(X_train, y_train)

    # Predict
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    # Metrics
    acc = accuracy_score(y_test, y_pred)
    f1  = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)

    print("\n" + "=" * 50)
    print("DIABETES MODEL — EVALUATION RESULTS")
    print("=" * 50)
    print(f"  Accuracy : {acc:.4f}  ({acc*100:.1f}%)")
    print(f"  F1-score : {f1:.4f}  ({f1*100:.1f}%)")
    print(f"  ROC-AUC  : {auc:.4f}  ({auc*100:.1f}%)")
    print(f"  PR-AUC   : {average_precision_score(y_test, y_prob):.4f}")
    print(f"  Brier score: {brier_score_loss(y_test, y_prob):.4f}")
    print()
    print(classification_report(
        y_test, y_pred,
        target_names=["No Diabetes", "Diabetes"],
    ))

    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, "diabetes_model.pkl") if balanced else MODEL_PATH
    joblib.dump(clf, model_path)
    print(f"\nModel saved to {model_path}")

    # Also save the feature column order — needed at inference time
    feature_path = os.path.join(MODEL_DIR, "diabetes_feature_cols.pkl" if balanced else "diabetes_feature_cols_unweighted.pkl")
    joblib.dump(feature_cols, feature_path)
    print(f"Feature column order saved to {feature_path}")

    return acc, f1, auc


# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--balanced", action="store_true", help="Train and replace the active balanced model")
    args = parser.parse_args()
    df, feature_cols = load_and_preprocess(DATA_PATH)
    train_model(df, feature_cols, balanced=args.balanced)
