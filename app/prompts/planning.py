"""
Planner prompt fragments.

Used by app/agent/planner.py to build per-turn prompts when we need the LLM
to explicitly decide between retrieving vs answering.

In practice, Gemini's native tool-calling handles most of the "what next"
reasoning implicitly: if it emits a function_call, we execute the tool;
otherwise we treat its text as the final answer. So the planner is mostly
a thin wrapper around the LLM response — these prompts are reserved for
explicit "should I refine the query?" decisions.
"""

from __future__ import annotations


EVALUATE_EVIDENCE_PROMPT = """\
Given the following retrieved evidence and the original question, decide
if the evidence is sufficient to answer confidently.

Question: {question}

Evidence:
{evidence}

Respond with EXACTLY one of:
- SUFFICIENT
- INSUFFICIENT: <one-sentence reason>

If INSUFFICIENT, also suggest a refined query on a new line:
- REFINED_QUERY: <new query>
"""


def build_evaluate_prompt(question: str, evidence: str) -> str:
    return EVALUATE_EVIDENCE_PROMPT.format(question=question, evidence=evidence)