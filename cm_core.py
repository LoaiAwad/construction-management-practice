"""
Core grading and explanation logic for the Construction Management (CM)
practice tool. Deliberately has no Streamlit dependency, so this module can
be safely imported by both cm_app.py (the web UI) and eval_explanations.py
(the eval script) without triggering any UI side effects.
"""

import json
import anthropic


def get_client(api_key=None):
    """Returns an Anthropic client. If api_key is given (e.g. from
    st.secrets on Streamlit Cloud), uses that; otherwise falls back to the
    ANTHROPIC_API_KEY environment variable."""
    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    return anthropic.Anthropic()


def grade_answer(q, student_answer, client=None):
    """Correct/Wrong grading -- multiple-choice checked directly against the
    known answer letter (no API call needed)."""
    if q["type"] == "multiple_choice":
        given_letter = student_answer.strip().upper()[:1]
        correct = given_letter == q["answer"]
        feedback = f"Correct answer: ({q['answer']}) {q['options'].get(q['answer'], '')}"
        return correct, feedback

    # Open-ended fallback (not used by the current CM bank, all questions
    # are multiple-choice, but kept for future question types)
    client = client or get_client()
    prompt = f"""You are grading a student's answer to a construction
management practice question.

Question: {q['prompt']}

Reference solution/explanation: {q['solution']}

Student's answer: {student_answer}

Decide if the student's final answer is correct. Respond with ONLY a JSON
object: {{"correct": true or false, "feedback": "one short sentence"}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(text)
        return bool(result["correct"]), result["feedback"]
    except (json.JSONDecodeError, KeyError, ValueError):
        return False, f"(Could not auto-grade cleanly) Raw response: {text}"


def generate_explanation(q, student_letter, correct, client=None):
    """Generates a short, personalized explanation reacting to the
    student's specific choice -- not just the book's canned explanation.
    If the student was wrong, it addresses why their specific choice was
    wrong AND why the correct answer is right. If correct, it briefly
    reinforces the key reasoning.

    Grounded in the book's own reference explanation (q['solution']) so it
    doesn't invent facts not supported by the source material.
    """
    client = client or get_client()

    student_choice_text = q["options"].get(student_letter.upper(), "(no valid option selected)")
    correct_letter = q["answer"]
    correct_text = q["options"].get(correct_letter, "")

    prompt = f"""You are a construction management tutor. A student just
answered a practice question.

Question: {q['prompt']}

Options:
{chr(10).join(f"{letter}. {text}" for letter, text in q['options'].items())}

Correct answer: {correct_letter}. {correct_text}
Reference explanation (from the course material): {q['solution']}

Student's answer: {student_letter}. {student_choice_text}
Student was: {"CORRECT" if correct else "INCORRECT"}

Write a short (2-4 sentence), personalized explanation reacting to this
specific student's choice:
- If correct: briefly reinforce the key reasoning, in your own words.
- If incorrect: explain specifically why their chosen option is wrong,
  AND why the correct answer is right. Don't just repeat the reference
  explanation verbatim -- paraphrase it in your own words, tailored to
  their specific wrong choice.

Stay strictly consistent with the reference explanation -- do not
introduce facts, rules, or reasoning that contradict or go beyond it.

Respond with ONLY the explanation text, no preamble, no JSON."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
