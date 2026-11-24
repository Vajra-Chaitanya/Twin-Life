from evaluation.eval_scenarios import Case, evaluate

HELD_OUT = [
    Case("health", "Lately I've been feeling exhausted", "h"),
    Case("health", "my legs ache after work", "h"),
    Case("health", "I've been coughing for a week", "h"),
    Case("health", "Doctor says my sugar is borderline", "h"),
    Case("health", "I was diagnosed with high bp last month", "h", events=("condition",)),
    Case("health", "I dropped 3 kg", "h", events=("weight",)),
    Case("health", "I began cycling to office", "h", events=("habit",)),
    Case("health", "What if I lose 8 kg?", "h", scenario="health"),
    Case("health", "Is 140/95 dangerous?", "h", scenario="health"),
    Case("health", "My brother has diabetes, should I get tested?", "h"),
    Case("finance", "Got a raise of 10%", "f", events=("income",)),
    Case("finance", "I got fired today", "f", events=("income",), needs=True),
    Case("finance", "Can I buy a scooter for 90k?", "f", scenario="purchase"),
    Case("finance", "Is a 20000 EMI for a flat okay?", "f", scenario="emi"),
    Case("finance", "Thinking of a 2 lakh vacation", "f", scenario="purchase"),
    Case("finance", "My house rent went up by 2500", "f", events=("expense",)),
    Case("finance", "I received a 50k bonus", "f", events=("savings",)),
    Case("finance", "My savings are now 6 lakh", "f", events=("savings",)),
    Case("finance", "how much money is left after expenses", "f"),
    Case("finance", "What if my expenses go up by 8000 per month?", "f", scenario="expense"),
    Case("finance", "Should I invest 5000 a month in mutual funds?", "f"),
    Case("finance", "I closed my bike loan of EMI 3000", "f", events=("loan_closed",)),
    Case("insurance", "Is my sum insured enough?", "i"),
    Case("insurance", "My sum insured is now 12 lakh", "i", events=("cover",)),
    Case("insurance", "I dropped the hospital cash rider", "i", events=("rider",)),
    Case("insurance", "What if I take 20 lakh cover?", "i", scenario="insurance"),
    Case("insurance", "Premium went up by 15% this year", "i", events=("premium",)),
    Case("insurance", "Do I have enough coverage for a family of four?", "i"),
    Case("insurance", "what riders should I add", "i"),
    Case("insurance", "My policy got cancelled", "i", events=("cover",), needs=True),
    Case("cross", "Will my insurance pay for a knee surgery costing 3 lakh?", "hfi", scenario="purchase"),
    Case("cross", "I had a heart attack, will my premium go up?", "hi", events=("condition",)),
    Case("cross", "My hospital bill was 1.5 lakh", "hfi", events=("medical_bill",)),
    Case("cross", "Can I afford my mother's treatment of 2 lakh?", "hfi", scenario="purchase"),
    Case("cross", "My medicines cost 4000 a month now", "hf", events=("expense",)),
    Case("cross", "I got a 25% hike, should I upgrade my insurance?", "fi", events=("income",)),
    Case("cross", "what about 8000?", "f", prev="Is an EMI of 12000 ok for me?", scenario="emi"),
    Case("cross", "7000 per month", "hfi", prev="My medical costs went up", prev_pending=True, events=("expense",)),
    Case("cross", "Why?", "i", prev="Should I add a critical illness rider?"),
    Case("cross", "I feel weak", "h", prev="What if I take a 10000 EMI?"),
    Case("cross", "had a surgery and paid 3 lakshs", "hfi", events=("medical_bill",)),
    Case("finance", "i took it from my aunt", "hfi", prev="had a surgery and paid 3 lakshs", events=("borrowed",)),
    Case("finance", "ill pay my aunt within next 3 month", "f", events=("repayment",), needs=True),
    Case("finance", "i got promotion ill extra 50k every month", "f", events=("income",)),
    Case("health", "I had dengue and was hospitalized for 5 days", "h", events=("illness",)),
    Case("health", "I fractured my leg", "h", events=("illness",)),
    Case("health", "I got covid last month", "h", events=("illness",)),
    Case("health", "My mother had dengue", "h"),
    Case("finance", "I lent 50k to my friend", "f", events=("lent",)),
    Case("finance", "I subscribed to Netflix for 649 per month", "f", events=("subscription",)),
    Case("finance", "I cancelled my Spotify subscription of 119 a month", "f", events=("subscription",)),
    Case("cross", "I joined a gym, membership is 2000 per month", "hf", events=("subscription", "habit")),
    Case("insurance", "I took a term plan of 1 crore", "i", events=("policy",)),
    Case("insurance", "I took bike insurance for 2500 a year", "i", events=("policy",)),
    Case("insurance", "I cancelled my car insurance", "i", events=("policy",)),
    Case("finance", "my friend returned the money", "f", events=("settled",), needs=True),
    Case("health", "My HbA1c is 6.4", "h", events=("glucose",)),
]

if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    results = [evaluate(c) for c in HELD_OUT]
    print(f"held-out {sum(r['ok'] for r in results)}/{len(results)}")
    for r in results:
        if not r["ok"]:
            diff = {k: (r["got"][k], r["want"][k]) for k in r["want"] if r["got"][k] != r["want"][k]}
            print(f"FAIL {r['case'].text!r}  got/want: {diff}")
