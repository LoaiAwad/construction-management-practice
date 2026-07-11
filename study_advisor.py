"""
Study Advisor Agent
--------------------
A genuine multi-step tool-calling agent (not a single prompt->response call).
Given a student's session results, it autonomously decides which tools to
call -- checking category performance, checking what's available in the
question bank -- before producing a final personalized study
recommendation.

This is architecturally different from generate_explanation() in
cm_core.py: that's one request in, one response out. This is a loop where
Claude decides what information it needs, requests it via tool calls,
receives results, and continues reasoning until it's ready to answer.
"""

import json
import anthropic

MODEL = "claude-sonnet-4-6"


# ---------- Tool implementations ----------
# These are plain Python functions. The agent decides when (and whether)
# to call each one -- it is not a fixed sequence.

def get_category_breakdown(session_log):
    """Returns per-category correct/total counts from this session."""
    breakdown = {}
    for entry in session_log:
        cat = entry["topic"]
        breakdown.setdefault(cat, {"correct": 0, "total": 0})
        breakdown[cat]["total"] += 1
        if entry["was_correct"]:
            breakdown[cat]["correct"] += 1
    return breakdown


def get_bank_stats(bank, category):
    """Returns how many questions exist in the bank for a given category,
    so the agent knows whether more practice is actually available."""
    topic_data = bank.get(category)
    if not topic_data:
        return {"category": category, "available_questions": 0}
    return {"category": category, "available_questions": len(topic_data["questions"])}


TOOLS = [
    {
        "name": "get_category_breakdown",
        "description": "Get the student's correct/total counts broken down by category for this session.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_bank_stats",
        "description": "Get how many practice questions are available in the question bank for a specific category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "The category name, e.g. 'Risk Management'"}
            },
            "required": ["category"],
        },
    },
]


def run_tool(name, tool_input, session_log, bank):
    if name == "get_category_breakdown":
        return get_category_breakdown(session_log)
    if name == "get_bank_stats":
        return get_bank_stats(bank, tool_input["category"])
    return {"error": f"unknown tool {name}"}


def run_study_advisor(session_log, bank, client=None, max_turns=6):
    """Runs the agent loop. Returns (final_text, transcript) where
    transcript is a list of the tool calls made, for transparency/debugging."""
    client = client or anthropic.Anthropic()

    messages = [{
        "role": "user",
        "content": (
            "You are a study advisor for a construction management exam "
            "practice tool. A student just finished a practice session. "
            "Use the available tools to check their performance by "
            "category and check what further practice is available, then "
            "give them a short, specific, encouraging study recommendation "
            "(2-4 sentences) naming their weakest category and confirming "
            "there are more questions available for it. If a weak category "
            "has zero questions available, say so honestly instead of "
            "recommending it."
        ),
    }]

    transcript = []

    for _ in range(max_turns):
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            # Claude produced its final answer
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            return final_text, transcript

        # Claude wants to call one or more tools -- run them and feed results back
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input, session_log, bank)
                transcript.append({"tool": block.name, "input": block.input, "result": result})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})

    return "(Agent did not reach a final answer within the turn limit.)", transcript
