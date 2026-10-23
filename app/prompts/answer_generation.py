"""Final answer generation prompt."""

from __future__ import annotations


ANSWER_GENERATION_PROMPT = """\
Based on the retrieved evidence and prior conversation, write a final answer
to the user's question.

Rules:
- Be concise and direct.
- Cite sources as [doc_<id>:page <n>] inline next to factual claims.
- If evidence is insufficient, say "I could not find sufficient information
  in the knowledge base to answer this question."
- Do not invent citations or claim a document says something it does not.

Question:
{question}

Retrieved evidence:
{evidence}

Write the answer:
"""


def build_answer_prompt(question: str, evidence: str) -> str:
    return ANSWER_GENERATION_PROMPT.format(question=question, evidence=evidence)