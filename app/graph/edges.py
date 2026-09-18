from typing import Any

from langgraph.graph import END, START


CLASSIFIER_NODE = "classifier"
KNOWLEDGE_NODE = "knowledge"
SOLUTION_NODE = "solution"
RESPONSE_NODE = "response"


def add_workflow_edges(builder: Any) -> None:
    builder.add_edge(START, CLASSIFIER_NODE)
    builder.add_edge(CLASSIFIER_NODE, KNOWLEDGE_NODE)
    builder.add_edge(KNOWLEDGE_NODE, SOLUTION_NODE)
    builder.add_edge(SOLUTION_NODE, RESPONSE_NODE)
    builder.add_edge(RESPONSE_NODE, END)
