#!/usr/bin/env python3
"""
AEC - analysis/train_model.py

Trains a Random Forest relevance classifier on labeled artifact
features, compares against baselines (keyword rule, Logistic
Regression, SVM), runs a feature ablation study, and computes
SHAP explanations.

Requires labels: run extract_features.py first, then open the
resulting features.csv and fill in a 'manual_label' column
(0 = not relevant, 1 = relevant) based on your own judgment as
an annotator. If you have a second annotator, save their labels
in a separate column ('manual_label_2') to compute Cohen's kappa.

Install requirements (inside a venv is fine, or --break-system-packages):
    pip3 install scikit-learn pandas shap --user --break-system-packages

Usage:
    python3 analysis/train_model.py --features ~/Desktop/lineageos_pilot/features.csv
"""

import argparse
import os
import sys

import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    cohen_kappa_score,
)
from sklearn.preprocessing import LabelEncoder


FEATURE_COLS = ["artifact_type", "file_size", "recency_days",
                 "deletion_state", "storage_location", "keyword_score"]


def load_and_prepare(csv_path, label_col):
    df = pd.read_csv(csv_path)

    if label_col not in df.columns:
        print(f"[!] Column '{label_col}' not found in {csv_path}.")
        print(f"    Available columns: {list(df.columns)}")
        print(f"    Add a '{label_col}' column (0/1) before running this script.")
        print(f"    Tip: as a starting point you can copy 'auto_label' into '{label_col}'")
        print(f"    then manually correct entries you disagree with.")
        sys.exit(1)

    # Encode categorical columns
    df_enc = df.copy()
    encoders = {}
    for col in ["artifact_type", "deletion_state", "storage_location"]:
        le = LabelEncoder()
        df_enc[col] = le.fit_transform(df_enc[col].astype(str))
        encoders[col] = le

    X = df_enc[FEATURE_COLS]
    y = df_enc[label_col].astype(int)
    return df, X, y, encoders


def keyword_baseline(df):
    """Rule-based baseline: relevant if keyword_score > 0."""
    return (df["keyword_score"] > 0).astype(int)


def evaluate(y_true, y_pred, name):
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    print(f"{name:30s} Acc={acc:.3f}  Prec={prec:.3f}  Rec={rec:.3f}  F1={f1:.3f}")
    return {"method": name, "accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


def run_cv(model, X, y, k=5):
    """k-fold cross-validated predictions. Falls back to smaller k if dataset is tiny."""
    n_splits = min(k, y.value_counts().min()) if y.nunique() > 1 else 2
    n_splits = max(2, n_splits)
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    try:
        preds = cross_val_predict(model, X, y, cv=skf)
    except ValueError as e:
        print(f"[!] CV failed ({e}) — falling back to a single train/test fit (dataset too small for CV).")
        model.fit(X, y)
        preds = model.predict(X)
    return preds, n_splits


def ablation_study(X, y, k):
    print("\n--- Feature Ablation Study (Macro-F1, Random Forest) ---")
    groups = {
        "Full feature set": FEATURE_COLS,
        "Without type": [c for c in FEATURE_COLS if c != "artifact_type"],
        "Without temporal (recency)": [c for c in FEATURE_COLS if c != "recency_days"],
        "Without content (keyword_score)": [c for c in FEATURE_COLS if c != "keyword_score"],
        "Without structural (storage/deletion)": [c for c in FEATURE_COLS if c not in
                                                    ["storage_location", "deletion_state"]],
    }
    results = {}
    for name, cols in groups.items():
        model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
        preds, _ = run_cv(model, X[cols], y, k)
        f1 = f1_score(y, preds, average="macro", zero_division=0)
        results[name] = f1
        print(f"  {name:40s} Macro-F1={f1:.3f}")
    return results


def run_shap_explanation(X, y, df):
    try:
        import shap
    except ImportError:
        print("\n[!] shap not installed — skipping explainability step.")
        print("    Install with: pip3 install shap --user --break-system-packages")
        return None

    model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    model.fit(X, y)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    # shap_values for binary RF classifier: list [class0, class1] or array depending on sklearn/shap version
    if isinstance(shap_values, list):
        sv = shap_values[1]
    else:
        sv = shap_values

    top_features = []
    for i in range(len(X)):
        row_shap = sv[i]
        top_idx = np.argmax(np.abs(row_shap))
        top_features.append(FEATURE_COLS[top_idx])

    df = df.copy()
    df["shap_top_feature"] = top_features

    out_path = "shap_top_features.csv"
    df[["artifact_id", "content_snippet", "shap_top_feature"]].to_csv(out_path, index=False)
    print(f"\nSHAP top-feature-per-artifact saved -> {out_path}")
    print("Review this against your own reasoning for why each artifact was")
    print("marked relevant to compute your 'explanation agreement %' metric.")
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True, help="Path to features.csv from extract_features.py")
    parser.add_argument("--label-col", default="manual_label", help="Column name containing 0/1 labels")
    parser.add_argument("--kfold", type=int, default=5)
    parser.add_argument("--label-col-2", default=None, help="Second annotator's label column, for Cohen's kappa")
    args = parser.parse_args()

    df, X, y, encoders = load_and_prepare(args.features, args.label_col)
    n = len(df)
    print(f"Loaded {n} artifacts. Label distribution:\n{y.value_counts().to_string()}\n")

    if n < 10:
        print("[!] WARNING: very small dataset (<10 artifacts). Results are illustrative")
        print("    only — report this explicitly as a pilot-study limitation.\n")

    # Cohen's kappa between two annotators, if provided
    if args.label_col_2 and args.label_col_2 in df.columns:
        kappa = cohen_kappa_score(df[args.label_col], df[args.label_col_2])
        print(f"Cohen's kappa (annotator agreement): {kappa:.3f}\n")

    print("=" * 65)
    print("TABLE I — Classification Performance")
    print("=" * 65)
    results = []

    # Keyword baseline
    kw_pred = keyword_baseline(df)
    results.append(evaluate(y, kw_pred, "Keyword/Rule-Based Baseline"))

    # Logistic Regression
    lr_preds, k_used = run_cv(LogisticRegression(max_iter=1000), X, y, args.kfold)
    results.append(evaluate(y, lr_preds, "Logistic Regression"))

    # SVM
    svm_preds, _ = run_cv(SVC(kernel="rbf"), X, y, args.kfold)
    results.append(evaluate(y, svm_preds, "SVM"))

    # Random Forest (XAMF core model)
    rf_preds, _ = run_cv(RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42), X, y, args.kfold)
    results.append(evaluate(y, rf_preds, "XAMF (Random Forest)"))

    print(f"\n(k-fold used: {k_used}, adjusted automatically for dataset size)")

    # Ablation study
    ablation_results = ablation_study(X, y, args.kfold)

    # SHAP explainability
    run_shap_explanation(X, y, df)

    # Save results table
    pd.DataFrame(results).to_csv("table1_classification_results.csv", index=False)
    pd.DataFrame(ablation_results.items(), columns=["configuration", "macro_f1"]).to_csv(
        "table3_ablation_results.csv", index=False
    )
    print("\nSaved: table1_classification_results.csv, table3_ablation_results.csv")


if __name__ == "__main__":
    main()
