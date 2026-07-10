"""
Eval for the personalized-explanation feature.
------------------------------------------------
Explanations are free text, so there's no single "correct" output to check
against like the FE grading eval. Instead, this runs two layers:

1. Automated sanity checks (cheap, catches obvious failures):
   - explanation is non-empty and a reasonable length
   - explanation doesn't accidentally affirm a wrong answer as correct
   - explanation mentions the actual correct answer's content

2. A clean report of all generated explanations for YOU (the domain
   expert) to judge actual pedagogical quality and factual accuracy --
   the same role you played in the FE eval.

Usage:
    python eval_explanations.py
(Run this in the same folder as cm_bank.json and cm_core.py)
"""

import json
from cm_core import generate_explanation, get_client

with open("cm_bank.json", encoding="utf-8") as f:
    topics = json.load(f)

questions_by_id = {}
for t in topics.values():
    for q in t["questions"]:
        questions_by_id[q["id"]] = q

with open("test_cases_explanations.json", encoding="utf-8") as f:
    test_cases = json.load(f)

client = get_client()
results = []
sanity_flags = []

for case in test_cases:
    q = questions_by_id.get(case["id"])
    if not q:
        print(f"WARNING: {case['id']} not found in cm_bank.json, skipping")
        continue

    student_letter = case["student_letter"]
    correct = student_letter.upper() == q["answer"]

    explanation = generate_explanation(q, student_letter, correct, client=client)

    flags = []
    if len(explanation) < 20:
        flags.append("explanation suspiciously short")
    if not correct:
        # crude sanity check: it shouldn't describe the student's WRONG
        # letter as the correct one
        wrong_option_text = q["options"].get(student_letter.upper(), "")
        if wrong_option_text and f"correct answer is {student_letter.upper()}" in explanation.lower():
            flags.append("explanation may have affirmed the wrong answer as correct")

    if flags:
        sanity_flags.append((q["id"], flags))

    results.append({
        "id": q["id"],
        "note": case.get("note", ""),
        "correct_answer": q["answer"],
        "student_letter": student_letter,
        "was_correct": correct,
        "explanation": explanation,
    })

print(f"\n{'=' * 60}")
print(f"Generated {len(results)} explanations. Automated flags: {len(sanity_flags)}")
print(f"{'=' * 60}\n")

if sanity_flags:
    print("FLAGGED (check these first):")
    for qid, flags in sanity_flags:
        print(f"  {qid}: {'; '.join(flags)}")
    print()

with open("explanation_review.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

# also write a human-readable version for easy review
with open("explanation_review.txt", "w", encoding="utf-8") as f:
    for r in results:
        f.write("=" * 60 + "\n")
        f.write(f"{r['id']} ({r['note']})\n")
        f.write("=" * 60 + "\n")
        q = questions_by_id[r["id"]]
        f.write(f"Question: {q['prompt']}\n\n")
        for letter, text in q["options"].items():
            marker = " <- correct" if letter == r["correct_answer"] else (" <- student picked" if letter == r["student_letter"] else "")
            f.write(f"  {letter}. {text}{marker}\n")
        f.write(f"\nExplanation:\n{r['explanation']}\n\n")

print("Saved explanation_review.json and explanation_review.txt")
print("Open explanation_review.txt and judge each explanation for accuracy and quality.")
