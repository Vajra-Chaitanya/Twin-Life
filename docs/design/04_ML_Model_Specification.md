# 4. ML Model Specification
### The ONE model in the whole project — what it's trained on and why

## The decision
You use exactly **one** trained ML model, for the Health Twin's core cardiometabolic risk prediction. Every other score in the system (diabetes indicator, hypertension stage, obesity class, all Finance metrics, all Insurance metrics) comes from formulas/rules, not additional models (see Doc 3).

## Dataset
**Kaggle "Cardiovascular Disease" dataset** (`cardio_train.csv`, ~70,000 rows).

This is the right choice because it's the one public dataset that already contains every shared metabolic risk-factor feature in one place, plus a real labeled outcome — you don't need to merge multiple mismatched datasets or fabricate labels.

## Features (input, X)
| Column | Source |
|---|---|
| age | dataset |
| gender | dataset |
| BMI | derived from height + weight (both in dataset) |
| ap_hi (systolic BP) | dataset |
| ap_lo (diastolic BP) | dataset |
| cholesterol (categorical: normal/above/well above) | dataset |
| gluc (categorical: normal/above/well above) | dataset |
| smoke | dataset |
| alco | dataset |
| active | dataset |

## Target (output, y)
**`cardio`** (0/1) — the dataset's real labeled cardiovascular risk outcome.

## Model
`RandomForestClassifier` (scikit-learn). Simple to train, trains in seconds on this data size, no GPU needed, and SHAP supports it directly for explainability.

## Training steps
1. Load `cardio_train.csv`, clean known data-entry outliers in height/weight/BP (documented issue in this dataset — filter unrealistic values).
2. Derive BMI from height/weight.
3. Split features (X) and target (y) as listed above.
4. Train/test split (e.g., 80/20).
5. Fit `RandomForestClassifier`.
6. Evaluate: accuracy, F1-score, ROC-AUC — record these for your report.
7. Run SHAP on the trained model → generate a feature-importance chart.
8. Save the model with `joblib` (`model.pkl`).

## How the other Health sub-scores relate to this same model
The model's input features (BMI, BP, glucose, cholesterol) are the same clinical signals used for diabetes/hypertension/obesity assessment. Instead of training three more models, those three sub-indicators are derived from the **same input features** using formulas (see Doc 3):
- Diabetes indicator ← `gluc` feature, threshold rule
- Hypertension stage ← `ap_hi`/`ap_lo`, ACC/AHA formula
- Obesity class ← BMI, WHO bands formula

## Report-ready sentence
> *"A single Random Forest model, trained on shared cardiometabolic risk factors (BMI, blood pressure, cholesterol, glucose, lifestyle indicators) from the Kaggle Cardiovascular Disease dataset, produces the core cardiovascular risk prediction. Diabetes, hypertension, and obesity sub-indicators are derived from the same input features using established clinical thresholds, avoiding redundant model training while keeping the Health Twin unified and explainable."*

*(Optional: if your report specifically needs to claim a "multi-label model," wrap the same Random Forest in `sklearn.multioutput.MultiOutputClassifier` with `cardio` + a derived diabetes-proxy label as two targets — still one model object, one training call. Only do this if required; the formula approach above is simpler and equally valid.)*

---
*Next: read `05_Simulation_Engines_and_Orchestrator_Routing.md` for how what-if scenarios and cross-domain queries actually run.*
