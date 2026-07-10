# Construction Management (CM) Practice

A web app for practicing construction management exam questions, with instant grading and AI-generated personalized explanations.

**Live app:** https://cm-exampractice-questions.streamlit.app

## What it does

- Pick a topic (Project Management, Cost Management, Time Management, Risk Management, and 5 others) or practice across all of them
- Choose how many questions to attempt
- Answer multiple-choice questions and get instant grading
- After each answer, Claude generates a **personalized explanation** — not just the canned textbook answer, but one that specifically addresses *why the option you picked* was right or wrong
- See your final score at the end of the session

## Why the personalized explanations

A plain answer key tells you "the answer is B." It doesn't tell you why the answer you actually picked was wrong, which is the more useful thing to know when you're studying. This app sends both your choice and the correct answer to Claude, grounded in the source material's own explanation, and asks for a short, specific reaction — while explicitly instructing it to stay consistent with the source material rather than inventing new reasoning.

## Tech stack

- **Python** + **Streamlit** for the web interface
- **Anthropic Claude API** (`claude-sonnet-4-6`) for generating explanations
- Question bank extracted and cleaned from source material, stored as structured JSON

## Project structure

```
cm_app.py                        Streamlit web app (UI, session flow)
cm_core.py                       Grading + explanation-generation logic (no Streamlit dependency,
                                  so it's reusable by both the app and the eval script)
cm_bank.json                     Question bank (45 questions, 9 categories)
eval_explanations.py             Eval script for the explanation feature
test_cases_explanations.json     13 test cases (one per category, mix of correct/incorrect answers)
requirements.txt                 Python dependencies
```

## Eval

Since the explanation feature is free-text (not a simple right/wrong check), it's evaluated in two layers:

1. **Automated sanity checks** — catches obvious failures (empty output, affirming a wrong answer as correct)
2. **Human review** — `eval_explanations.py` generates `explanation_review.txt`, a side-by-side of each question, the student's answer, and Claude's explanation, for manual judgment of accuracy and quality

Run the eval yourself:
```bash
python eval_explanations.py
```

## Running locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here   # or set it as an environment variable on Windows
streamlit run cm_app.py
```

## Known limitations

- Question bank is a curated subset (45 of ~350+ available questions in the source material), selected to avoid tables/charts that don't extract cleanly from Word documents
- No persistent user accounts or progress tracking across sessions
- Explanations are generated fresh each time (not cached), so repeated runs of the same question may produce slightly different wording
