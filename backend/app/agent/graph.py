"""LangGraph workflow for planning, corpus retrieval, tool use, synthesis, and critique."""

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

import yaml
from langgraph.graph import END, START, StateGraph
from opentelemetry import trace

from app.agent.llm import chat
from app.agent.tools import run_tool
from app.instrumentation.setup import current_prompt_version

tracer = trace.get_tracer("agenttrace.graph")
CORPUS_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "corpus"
LONG_DOCUMENT_WORDS = 240


class Document(TypedDict):
    doc_id: str
    title: str
    text: str
    score: float


class AgentState(TypedDict, total=False):
    question: str
    feedback: str
    plan: str
    search_query: str
    calculation: str | None
    documents: list[Document]
    tool_result: str
    answer: str
    supported: bool
    revision: int
    corpus_ids: list[str]


def load_corpus() -> list[dict[str, str]]:
    documents = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", raw, re.S)
        if not match:
            continue
        metadata = yaml.safe_load(match.group(1)) or {}
        doc_id = metadata.get("doc_id")
        if not doc_id:
            raise ValueError(f"Missing doc_id frontmatter in {path}")
        documents.append({"doc_id": str(doc_id), "title": str(metadata.get("title", path.stem)), "text": match.group(2).strip()})
    if not documents:
        raise RuntimeError(f"No markdown corpus documents found in {CORPUS_DIR}")
    return documents


def keyword_search(query: str, limit: int = 4, doc_ids: list[str] | None = None) -> list[Document]:
    """A small normalized term-frequency/inverse-document-frequency ranker."""
    tokenize = lambda s: re.findall(r"[a-z0-9]+", s.lower())
    query_terms = set(tokenize(query))
    corpus = load_corpus()
    if doc_ids is not None:
        allowed = set(doc_ids)
        corpus = [document for document in corpus if document["doc_id"] in allowed]
    term_sets = [set(tokenize(d["text"] + " " + d["title"])) for d in corpus]
    scored: list[Document] = []
    for doc, terms in zip(corpus, term_sets):
        score = sum((1 + (len(corpus) / (1 + sum(term in ts for ts in term_sets)))) for term in query_terms if term in terms)
        if score:
            scored.append({**doc, "score": float(score)})
    return sorted(scored, key=lambda d: d["score"], reverse=True)[:limit]


def _json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        value = json.loads(match.group())
        if isinstance(value, dict):
            return value
    raise ValueError("Model response was not a JSON object")


def _summarize_long_documents(documents: list[Document], tier: str) -> list[Document]:
    summarized = []
    child_graph = build_summarizer(tier)
    for doc in documents:
        if len(doc["text"].split()) > LONG_DOCUMENT_WORDS:
            result = child_graph.invoke({"document": doc["text"], "title": doc["title"]})
            summarized.append({**doc, "text": result["summary"]})
        else:
            summarized.append(doc)
    return summarized


def build_summarizer(tier: str):
    class SummaryState(TypedDict, total=False):
        document: str
        title: str
        summary: str

    def summarize(state: SummaryState) -> dict[str, str]:
        with tracer.start_as_current_span("agenttrace.summarize") as span:
            span.set_attribute("agenttrace.operation", "summarize")
            summary = chat(
                [
                    {"role": "system", "content": "Summarize the supplied reference document faithfully. Keep its operational facts and do not add facts."},
                    {"role": "user", "content": f"Title: {state['title']}\n\n{state['document']}"},
                ],
                tier=tier,
                purpose="summarize",
            )
            return {"summary": summary}

    graph = StateGraph(SummaryState)
    graph.add_node("summarize", summarize)
    graph.add_edge(START, "summarize")
    graph.add_edge("summarize", END)
    return graph.compile()


Node = Callable[[AgentState], dict[str, Any]]


def build_agent(tier: str, *, node_wrapper: Callable[[str, Node], Node] | None = None):
    def plan(state: AgentState) -> dict[str, Any]:
        with tracer.start_as_current_span("agenttrace.plan") as span:
            span.set_attribute("agenttrace.operation", "plan")
            system_prompt = (
                "Plan a concise evidence-based answer. Return only JSON with search_query, calculation (expression or null), and plan. Do not answer yet."
                if current_prompt_version() == "terse"
                else "Plan a thorough evidence-based answer. Identify the facts to retrieve and any arithmetic needed. Return only JSON with keys search_query, calculation (an arithmetic expression or null), and plan. Do not answer the question yet."
            )
            raw = chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Question: {state['question']}\nPrevious critique: {state.get('feedback', 'none')}"},
                ],
                tier=tier,
                purpose="plan",
            )
            parsed = _json_object(raw)
            return {"plan": str(parsed.get("plan", "")), "search_query": str(parsed.get("search_query", state["question"])), "calculation": parsed.get("calculation")}

    def retrieve(state: AgentState) -> dict[str, Any]:
        with tracer.start_as_current_span("agenttrace.retrieve") as span:
            span.set_attribute("agenttrace.operation", "retrieve")
            query = state.get("search_query", state["question"])
            documents = keyword_search(query, doc_ids=state.get("corpus_ids"))
            if not documents and query != state["question"]:
                query = state["question"]
                documents = keyword_search(query, doc_ids=state.get("corpus_ids"))
            span.set_attribute("gen_ai.operation.name", "retrieval")
            span.set_attribute("gen_ai.data_source.id", "agenttrace-corpus")
            span.set_attribute("gen_ai.retrieval.query.text", query)
            span.set_attribute("gen_ai.retrieval.documents", json.dumps([{"id": d["doc_id"], "score": d["score"]} for d in documents]))
            span.set_attribute("agenttrace.retrieval.document_bodies", json.dumps([d["text"] for d in documents], ensure_ascii=False))
            return {"documents": documents}

    def summarize(state: AgentState) -> dict[str, Any]:
        return {"documents": _summarize_long_documents(state.get("documents", []), tier)}

    def tool(state: AgentState) -> dict[str, str]:
        with tracer.start_as_current_span("execute_tool calculator") as span:
            span.set_attribute("agenttrace.operation", "execute_tool")
            span.set_attribute("gen_ai.operation.name", "execute_tool")
            span.set_attribute("gen_ai.tool.name", "calculator")
            span.set_attribute("gen_ai.tool.type", "function")
            span.set_attribute("gen_ai.agent.name", "agenttrace")
            span.set_attribute("agenttrace.tool.name", "calculator")
            return {"tool_result": run_tool(state.get("calculation"))}

    def synthesize(state: AgentState) -> dict[str, str]:
        with tracer.start_as_current_span("agenttrace.synthesize") as span:
            span.set_attribute("agenttrace.operation", "synthesize")
            references = "\n\n".join(f"[{d['doc_id']}] {d['title']}\n{d['text']}" for d in state.get("documents", []))
            prompt = (
                f"Question: {state['question']}\nPlan: {state.get('plan', '')}\n"
                f"Tool result: {state.get('tool_result', '')}\n"
                f"Retrieved reference text:\n{references or '(No matching reference documents.)'}\n\n"
                + ("Use only supported claims. Cite doc_id values. Label calculations. If evidence is missing, say so."
                   if current_prompt_version() == "terse" else
                   "Answer using only claims supported by the retrieved reference text. Clearly label any arithmetic tool result. Cite supporting doc_id values inline. If the reference text does not support an answer, say so.")
            )
            synthesis_system = (
                "Be concise and ground factual claims only in supplied references."
                if current_prompt_version() == "terse"
                else "You are a careful technical support agent. Ground factual statements only in the supplied retrieved reference text. Explain the answer clearly and distinguish evidence from calculations."
            )
            answer = chat(
                [{"role": "system", "content": synthesis_system}, {"role": "user", "content": prompt}],
                tier=tier,
                purpose="synthesize",
            )
            return {"answer": answer}

    def critique(state: AgentState) -> dict[str, Any]:
        with tracer.start_as_current_span("agenttrace.critique") as span:
            span.set_attribute("agenttrace.operation", "critique")
            critique_system = (
                "Check support against the evidence. Return JSON with supported and feedback."
                if current_prompt_version() == "terse"
                else "Judge whether each factual claim in the answer is supported by the supplied evidence. Return only JSON: {\"supported\": true|false, \"feedback\": \"short reason\"}."
            )
            raw = chat(
                [
                    {"role": "system", "content": critique_system},
                    {"role": "user", "content": f"Evidence:\n{chr(10).join(d['text'] for d in state.get('documents', []))}\n\nAnswer:\n{state.get('answer', '')}"},
                ],
                tier=tier,
                purpose="critique",
            )
            parsed = _json_object(raw)
            supported = bool(parsed.get("supported", False))
            revision = state.get("revision", 0) + (0 if supported else 1)
            span.set_attribute("agenttrace.critique.iteration", state.get("revision", 0) + 1)
            span.set_attribute("agenttrace.critique.hit_cap", not supported and revision >= 3)
            return {"supported": supported, "feedback": str(parsed.get("feedback", "")), "revision": revision}

    def after_critique(state: AgentState) -> str:
        return "done" if state.get("supported", False) or state.get("revision", 0) >= 3 else "revise"

    graph = StateGraph(AgentState)
    nodes: dict[str, Node] = {"plan": plan, "retrieve": retrieve, "summarize": summarize, "tool": tool, "synthesize": synthesize, "critique": critique}
    if node_wrapper is not None:
        nodes = {name: node_wrapper(name, node) for name, node in nodes.items()}
    for name, node in nodes.items():
        graph.add_node(name, node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "summarize")
    graph.add_edge("summarize", "tool")
    graph.add_edge("tool", "synthesize")
    graph.add_edge("synthesize", "critique")
    graph.add_conditional_edges("critique", after_critique, {"done": END, "revise": "plan"})
    return graph.compile()


def run_question(question: str, *, tier: str, max_revisions: int = 3, corpus_ids: list[str] | None = None, node_wrapper: Callable[[str, Node], Node] | None = None) -> dict[str, Any]:
    # A failed critique may send the graph through plan again at most three times.
    result = build_agent(tier, node_wrapper=node_wrapper).invoke({"question": question, "revision": 0, "corpus_ids": corpus_ids}, config={"recursion_limit": 6 * (max_revisions + 1) + 5})
    return {"answer": result.get("answer", ""), "supported": result.get("supported", False), "revision_count": result.get("revision", 0)}
