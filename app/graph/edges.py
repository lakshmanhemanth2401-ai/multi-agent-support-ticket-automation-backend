from typing import Any

from langgraph.graph import END, START


CLASSIFIER_NODE = "classifier"
KNOWLEDGE_NODE = "knowledge"
SOLUTION_NODE = "solution"
RESPONSE_NODE = "response"
REVIEW_RECORD_NODE = "review_record"
HUMAN_REVIEW_NODE = "human_review"


def add_workflow_edges(builder: Any) -> None:
    builder.add_edge(START, CLASSIFIER_NODE)
    builder.add_edge(CLASSIFIER_NODE, KNOWLEDGE_NODE)
    builder.add_edge(KNOWLEDGE_NODE, SOLUTION_NODE)
    builder.add_edge(SOLUTION_NODE, RESPONSE_NODE)
    builder.add_edge(RESPONSE_NODE, REVIEW_RECORD_NODE)
    builder.add_edge(REVIEW_RECORD_NODE, HUMAN_REVIEW_NODE)
    builder.add_conditional_edges(
        HUMAN_REVIEW_NODE,
        route_review_action,
        {"complete": END, "rework": SOLUTION_NODE},
    )


def route_review_action(state: dict[str, Any]) -> str:
    action = state.get("review_action")
    return "complete" if str(action) in {"approve", "edit"} else "rework"
