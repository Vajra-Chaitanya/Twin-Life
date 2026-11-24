# 3. Data Inputs and Twin Processing
### Exactly what you collect from the user, and how each field gets turned into a score

## 3A. Health Twin

**Inputs (onboarding form):**
| Field | Type | Example |
|---|---|---|
| Age | number | 34 |
| Gender | select | Male/Female/Other |
| Height (cm), Weight (kg) | number | 170, 78 |
| Systolic / Diastolic BP | number | 128 / 84 |
| Fasting blood glucose (mg/dL) | number | 105 |
| Total cholesterol (mg/dL) | number | 190 |
| Smoking status | select | Never/Former/Current |
| Physical activity level | select | Sedentary/Moderate/Active |
| Family history | multi-select | Diabetes, Heart Disease, None |
| Existing diagnosed conditions | multi-select | Diabetes, Hypertension, None |

**Processing:**
| Output | Method |
|---|---|
| BMI + obesity class | Formula (WHO bands) |
| Hypertension stage | Formula (ACC/AHA thresholds) |
| Cardiometabolic/CVD risk | **The one ML model** (see Doc 4) |
| Diabetes risk indicator | Formula (glucose threshold rule) |
| Overall Health Score (0-100) | Weighted combination of the above |

**Output shape:**
```json
{
  "bmi": 27.0, "obesity_class": "Overweight",
  "hypertension_stage": "Stage 1",
  "cardio_risk": {"probability": 0.42, "label": "Medium"},
  "diabetes_indicator": "Medium",
  "overall_health_score": 58
}
```

---

## 3B. Finance Twin

**Inputs:**
| Field | Type | Example |
|---|---|---|
| Monthly income | number | ₹65,000 |
| Monthly fixed expenses (rent/EMIs) | number | ₹20,000 |
| Monthly variable expenses | number | ₹15,000 |
| Current savings/investment balance | number | ₹1,50,000 |
| Total outstanding debt | number | ₹3,00,000 |
| Dependents | number | 2 |
| Employment type | select | Salaried/Self-employed |

**Processing — 100% formulas, no model:**
| Output | Formula |
|---|---|
| DTI Ratio | `(fixed_expenses + EMIs) / income` |
| Savings Rate | `(income − fixed − variable) / income` |
| Emergency Fund (months) | `savings_balance / (fixed + variable)` |
| Financial Stability Score (0-100) | Weighted combo of the above |
| Affordability Score (for a given cost) | `(disposable_income × months) / cost` |

**Output shape:**
```json
{
  "dti_ratio": 0.31, "savings_rate": 0.15,
  "emergency_fund_months": 4.3,
  "financial_stability_score": 66
}
```

---

## 3C. Insurance Twin

**Inputs:**
| Field | Type | Example |
|---|---|---|
| Current sum insured | number | ₹5,00,000 |
| Annual premium | number | ₹18,000 |
| Policy type | select | Individual/Family Floater |
| Existing riders | multi-select | Critical Illness, OPD, Maternity, None |
| Claims in last 12 months | number | 0 |

**Processing — 100% rule-based, depends on Health Twin's output for cost estimate:**
| Output | Logic |
|---|---|
| Estimated future medical cost | Lookup table keyed to Health Twin's risk labels |
| Coverage Adequacy Ratio | `sum_insured / estimated_future_cost` |
| Premium Affordability Ratio | `premium / income` (pulled from Finance Twin) |
| Rider Gap Flags | If health risk flagged but no matching rider exists |
| Insurance Adequacy Score (0-100) | Weighted combo of the above |

**Output shape:**
```json
{
  "estimated_future_cost": 40000,
  "coverage_adequacy_ratio": 12.5,
  "premium_affordability_ratio": 0.028,
  "rider_gaps": ["Critical Illness rider missing"],
  "insurance_adequacy_score": 74
}
```

---

## Why this three-twin split matters
Notice: **only the Health Twin uses an ML model.** Finance and Insurance are entirely formulas/rules — this is intentional, not a shortcut. DTI ratios and coverage-adequacy comparisons are inherently arithmetic problems with established standards, not pattern-recognition problems, so training a model there would add complexity without adding accuracy. This is a defensible engineering decision to state explicitly in your report.

---
*Next: read `04_ML_Model_Specification.md` for exactly how the one Health Twin model is trained.*
