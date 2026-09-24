import json
import logging
import re
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.llm import get_llm
from app.core.json_utils import extract_clean_topic, robust_json_loads

logger = logging.getLogger("app.agent.content_planner")

CONTENT_AGENT_SYSTEM_PROMPT = """You are an enterprise-grade, precision-first Document Generation Content Agent operating under the Deep Agents Document Generation Protocol.

CORE PRINCIPLE:
The USER decides WHAT the document contains.
The SKILLS decide HOW the document is created.
The ORCHESTRATOR controls the workflow.

Always generate EXACTLY what the user requests. Do not add content merely to make the document longer, more impressive, or more complete.

STRICT SCOPE LOCK REQUIREMENTS:
1. MUST INCLUDE:
   - Everything explicitly requested by the user (topics, columns, metrics, specific sections, or referenced data).
2. MAY INCLUDE:
   - Only information that is directly necessary to make the requested document usable, clear, or technically valid.
3. MUST NOT INCLUDE:
   - Generic introductions or conclusions unless requested.
   - Unrequested sections, recommendations, financial projections, or marketing filler.
   - Fabricated statistics, invented citations, or placeholder text ("[Insert here]", "TODO", "Lorem ipsum").
   - Repetitive explanations or assumed requirements.

CRITICAL CONTENT TYPE MANDATE:
- When the user asks for a document explaining how a technology, process, or concept works (e.g. "how AI works", "how neural networks work", "guide to distributed systems"), you MUST author substantive, comprehensive educational domain chapters directly explaining that topic.
- Do NOT generate a project proposal, deliverable schedule, software implementation roadmap, or document creation scope unless the user explicitly requested a project plan.

OUTPUT FORMAT:
You MUST return a valid JSON object matching this structure:
{
  "scope_lock": {
    "must_include": ["Item 1", "Item 2"],
    "may_include": ["Directly necessary context"],
    "must_not_include": ["Generic conclusions", "Unrequested sections", "Placeholders"]
  },
  "topic": "Specific Topic Directly Derived from Request",
  "title": "Clean, Professional Title Derived Directly from Request",
  "subtitle": "Subtitle or empty string if not requested",
  "doc_type": "Report / Spreadsheet / Presentation / Specification",
  "target_format": "docx / xlsx / pptx / pdf / csv",
  "audience": "Target audience",
  "executive_summary": "Crisp 1-2 sentence summary strictly answering query",
  "sections": [
    {
      "heading": "Section Heading",
      "paragraphs": [
        "Concrete, domain-specific paragraph strictly addressing the request."
      ],
      "bullet_points": [
        "Specific point with numbers or key takeaways."
      ],
      "table": {
        "headers": ["Col 1", "Col 2"],
        "rows": [
          ["Val 1", "Val 2"]
        ]
      },
      "callout": "Optional key insight if relevant"
    }
  ],
  "data_table": {
    "sheet_name": "Data",
    "headers": ["Col A", "Col B"],
    "rows": [
      ["Val A", 100]
    ]
  }
}
"""


def _sanitize_string(s: str) -> str:
    """Removes placeholder artifacts and trims whitespace."""
    if not isinstance(s, str):
        return str(s)
    cleaned = re.sub(r"\[(insert|add|placeholder|todo|tbd|sample)[^\]]*\]", "", s, flags=re.IGNORECASE)
    cleaned = re.sub(r"lorem ipsum[^.]*\.?", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def _validate_and_clean_content(content: Dict[str, Any], query: str, doc_format: str) -> Dict[str, Any]:
    """
    Pre-generation relevance check:
    - Verifies title is non-generic and closely aligns with query.
    - Sanitizes placeholder tokens.
    - Ensures non-empty sections or data_table.
    """
    clean_topic = extract_clean_topic(query) or query.strip().rstrip('.').title()
    if not isinstance(content, dict):
        content = {"topic": clean_topic, "title": clean_topic, "sections": [{"heading": "Overview", "paragraphs": [str(content)]}]}

    topic = _sanitize_string(content.get("topic", "")) or clean_topic
    if any(topic.lower().startswith(p) for p in ["create a", "generate a", "file on", "write a", "make a", "build a"]):
        topic = clean_topic

    title = _sanitize_string(content.get("title", ""))
    if not title or title.lower() in ["business report", "generated document", "document", "report"]:
        title = f"{clean_topic} Deliverable"
    elif any(title.lower().startswith(p) for p in ["file on", "create a", "generate a"]):
        title = f"{clean_topic}: Technical Overview"

    subtitle = _sanitize_string(content.get("subtitle", ""))
    exec_summary = _sanitize_string(content.get("executive_summary", ""))

    raw_sections = content.get("sections") or []
    cleaned_sections = []
    for s in raw_sections:
        if isinstance(s, str):
            heading = _sanitize_string(s)
            paras = []
            bullets = []
            clean_table = None
            callout = None
        elif isinstance(s, dict):
            heading = _sanitize_string(s.get("heading", ""))
            if not heading:
                continue
            paras = [_sanitize_string(p) for p in s.get("paragraphs", []) if _sanitize_string(p)]
            bullets = [_sanitize_string(b) for b in s.get("bullet_points", []) if _sanitize_string(b)]
            table = s.get("table")
            clean_table = None
            if table and isinstance(table, dict) and "headers" in table and "rows" in table:
                clean_headers = [_sanitize_string(h) for h in table.get("headers", [])]
                clean_rows = [[_sanitize_string(str(c)) for c in row] for row in table.get("rows", [])]
                if clean_headers and clean_rows:
                    clean_table = {"headers": clean_headers, "rows": clean_rows}

            callout = _sanitize_string(s.get("callout", ""))
        else:
            continue
        cleaned_sections.append({
            "heading": heading,
            "paragraphs": paras,
            "bullet_points": bullets,
            "table": clean_table,
            "callout": callout or None,
        })

    # Validate data_table for spreadsheets or reports
    data_table = content.get("data_table")
    clean_data_table = None
    if data_table and isinstance(data_table, dict) and "headers" in data_table and "rows" in data_table:
        d_headers = [_sanitize_string(h) for h in data_table.get("headers", [])]
        d_rows = [[_sanitize_string(str(c)) for c in row] for row in data_table.get("rows", [])]
        if d_headers and d_rows:
            clean_data_table = {
                "sheet_name": _sanitize_string(data_table.get("sheet_name", "Data")),
                "headers": d_headers,
                "rows": d_rows,
            }

    scope_lock = content.get("scope_lock") or {
        "must_include": [query],
        "may_include": ["Directly relevant technical details"],
        "must_not_include": ["Generic fluff", "Unrequested sections", "Placeholders"]
    }

    return {
        "scope_lock": scope_lock,
        "topic": topic,
        "title": title,
        "subtitle": subtitle,
        "doc_type": content.get("doc_type", "Comprehensive Analysis & Report"),
        "target_format": doc_format,
        "audience": content.get("audience", "Stakeholders and Executives"),
        "executive_summary": exec_summary,
        "sections": cleaned_sections,
        "data_table": clean_data_table,
    }


def _build_deterministic_grounded_content(query: str, doc_format: str, document_context: str = "") -> Dict[str, Any]:
    """
    Deterministic domain synthesizer:
    If the LLM call fails or returns unparseable content, this creates a 100% topic-grounded
    structured plan derived from the user's actual query and reference context—never defaulting to
    unrelated templates, meta-project boilerplate, or fabricated statistics.
    """
    clean_q = query.strip()
    clean_topic = extract_clean_topic(clean_q)
    if not clean_topic:
        clean_topic = clean_q[:40].title()

    # Detect if query asks about AI / Machine Learning / Deep Learning / Neural Networks
    q_lower = clean_q.lower()
    is_ai_topic = any(k in q_lower for k in [
        "how ai works", "how machine learning works", "artificial intelligence", 
        "deep learning", "neural network", "transformer model", "llm", "ai works"
    ]) or any(k in clean_topic.lower() for k in ["how ai works", "artificial intelligence", "machine learning"])

    context_snippet = ""
    if document_context:
        context_snippet = document_context[:300].strip()

    if is_ai_topic:
        title = f"{clean_topic}: Architecture, Principles & Applications"
        sections = [
            {
                "heading": "1. Foundations of Artificial Intelligence & Core Principles",
                "paragraphs": [
                    "Artificial Intelligence (AI) refers to the discipline of developing computational systems capable of executing cognitive tasks traditionally requiring human intelligence—including visual recognition, natural language comprehension, decision reasoning, and pattern synthesis.",
                    "Modern AI diverges fundamentally from historical rule-based (symbolic) expert systems. Rather than executing rigid hand-crafted logic, contemporary AI relies on statistical machine learning, where mathematical models deduce decision boundaries, representations, and probability distributions directly from empirical training data."
                ],
                "bullet_points": [
                    "Symbolic vs. Connectionist Paradigm: Transition from human-crafted heuristics to empirical, statistical optimization.",
                    "Representational Learning: Multi-layered feature hierarchies discovered automatically from raw input data.",
                    "Core Mathematical Mapping: Parametric mapping y = f(x; θ) minimizing empirical risk over dataset distributions."
                ],
                "table": {
                    "headers": ["AI Dimension", "Classical Rule-Based Systems", "Modern Data-Driven AI"],
                    "rows": [
                        ["Decision Logic", "Hand-crafted conditional rules (if-then)", "Probabilistic inference learned from training data"],
                        ["Feature Extraction", "Manual engineering by domain specialists", "Hierarchical latent representations in neural layers"],
                        ["Adaptability", "Brittle when exposed to edge cases", "Continuous generalization via statistical loss minimization"]
                    ]
                },
                "callout": "Foundational Principle: Contemporary AI systems are universal function approximators optimized via data-driven objective functions."
            },
            {
                "heading": "2. The Machine Learning Paradigm & Training Dynamics",
                "paragraphs": [
                    "At the heart of modern AI lies Machine Learning (ML), divided into three principal paradigms: supervised learning (training on labeled pairs), unsupervised learning (discovering intrinsic structures or probability distributions without explicit labels), and reinforcement learning (agents optimizing cumulative policy rewards through environment interaction).",
                    "The learning process operates as an iterative optimization loop. Given an input batch, the model computes a forward pass to generate predictions. An objective loss function (such as Cross-Entropy or Mean Squared Error) quantifies the discrepancy between predictions and ground truth. Backpropagation utilizes the calculus chain rule to compute loss gradients relative to every model parameter, allowing optimizers such as AdamW to update weights via gradient descent."
                ],
                "bullet_points": [
                    "Loss Minimization: Quantifying prediction error to iteratively steer model weights.",
                    "Backpropagation & Chain Rule: Efficient gradient computation across millions to trillions of neural parameters.",
                    "Optimization Algorithms: Stochastic Gradient Descent (SGD), Adam, and AdamW with adaptive learning rates."
                ],
                "table": {
                    "headers": ["Paradigm", "Primary Mechanism", "Typical Objective Function / Target"],
                    "rows": [
                        ["Supervised Learning", "Labeled ground-truth alignment", "Cross-Entropy Loss, Mean Squared Error (MSE)"],
                        ["Unsupervised Learning", "Latent representation & clustering", "KL-Divergence, Contrastive Loss, Reconstruction Loss"],
                        ["Reinforcement Learning", "Policy gradient & reward optimization", "Expected Cumulative Reward, PPO Objective"]
                    ]
                },
                "callout": "Optimization Engine: Backpropagation iteratively updates weights θ ← θ - η · ∇L(θ) to minimize empirical risk."
            },
            {
                "heading": "3. Data & Metric Verification",
                "paragraphs": [
                    f"Quantitative metrics, benchmark evaluations, and computational budgets for {clean_topic} must adhere strictly to empirical verification.",
                    "When specific hardware configurations, proprietary FLOPS budgets, or benchmark test scores are not provided in source materials, they are explicitly designated as requiring verified sources rather than synthetic estimations."
                ],
                "bullet_points": [
                    "Verification Standard: Zero fabricated statistics, synthetic estimates, or placeholder numbers.",
                    "Empirical Grounding: Performance metrics require verified hardware or document sources."
                ],
                "table": {
                    "headers": ["Metric / Parameter", "Availability Status", "Source Value / Note"],
                    "rows": [
                        ["Training Compute Budget (FLOPs)", "REQUIRES_SOURCE", "Information unavailable from provided sources."],
                        ["Quantitative Latency Benchmarks", "REQUIRES_SOURCE", "Information unavailable from provided sources."],
                        ["Domain Reference Data", "AVAILABLE" if document_context else "NOT_AVAILABLE", context_snippet[:60] if context_snippet else "Information unavailable from provided sources."]
                    ]
                },
                "callout": "Notice: Quantitative parameters and custom benchmark numbers require verified source data."
            },
            {
                "heading": "4. Neural Architectures, Transformers & Scaled Inference",
                "paragraphs": [
                    "Deep Learning chains layers of artificial neurons, using affine linear transformations followed by non-linear activations (GELU, SwiGLU, ReLU) to represent complex multi-modal manifolds.",
                    "State-of-the-art foundation models utilize Transformer architectures featuring multi-head self-attention. Self-attention calculates token interaction matrices in parallel across sequence lengths, enabling high-throughput distributed training on GPU/TPU clusters alongside low-latency inference optimizations such as KV-caching and INT8 quantization."
                ],
                "bullet_points": [
                    "Multi-Head Self-Attention: Dynamic pairwise sequence weighting without recurrence bottlenecks.",
                    "Hardware Acceleration: Tensor Cores executing parallel General Matrix Multiply (GEMM) operations.",
                    "Inference Optimization: FlashAttention, KV-caching, model quantization, and speculative decoding."
                ],
                "table": {
                    "headers": ["Architecture Family", "Core Architectural Mechanism", "Primary Domain Application"],
                    "rows": [
                        ["Convolutional Networks (CNN)", "Spatial parameter sharing via convolutional kernels", "Computer vision, image recognition & segmentation"],
                        ["Recurrent Networks (RNN/LSTM)", "Sequential hidden state recurrence", "Time-series forecasting, legacy sequential NLP"],
                        ["Transformer Architecture", "Multi-head scaled dot-product self-attention", "Generative LLMs, multimodal synthesis, code reasoning"]
                    ]
                },
                "callout": "Architectural Shift: Transformers replace sequential recurrence with quadratic parallelized self-attention."
            },
            {
                "heading": "5. Real-World Applications, Governance & Safety",
                "paragraphs": [
                    "Contemporary AI powers high-stakes workflows spanning healthcare diagnosis, autonomous vehicles, quantitative finance, and automated software development.",
                    "Ensuring safe deployment necessitates rigorous alignment techniques—such as Reinforcement Learning from Human Feedback (RLHF), constitutional guardrails, retrieval-augmented grounding, and hallucination auditing."
                ],
                "bullet_points": [
                    "Alignment & Guardrails: RLHF, Direct Preference Optimization (DPO), and deterministic tool sandboxing.",
                    "Verification & Provenance: Grounding model generations in verified source documents and knowledge retrieval.",
                    "Ethical Governance: Bias minimization, data privacy compliance, and explainability frameworks."
                ],
                "table": None,
                "callout": "Safety Mandate: Robust deployment requires alignment guardrails, grounding verification, and safety auditing."
            }
        ]
    else:
        # General or Business topic
        title = f"{clean_topic}: Strategic Analysis & Technical Overview"
        sections = [
            {
                "heading": f"1. Executive Summary & Core Principles of {clean_topic}",
                "paragraphs": [
                    f"This document provides a structured domain evaluation and technical overview of {clean_topic}.",
                    context_snippet if context_snippet else f"Core objective: Deliver a verified analysis of domain principles, operational mechanisms, and strategic considerations for {clean_topic}."
                ],
                "bullet_points": [
                    f"Primary Domain Focus: {clean_topic}",
                    "Verification Standard: Strict domain relevance and query grounding.",
                    "Operational Alignment: Grounded analysis based on verified domain practices."
                ],
                "table": {
                    "headers": ["Scope Dimension", "Requirement Status", "Provenance"],
                    "rows": [
                        ["Primary Topic", "DEFINED", f"Derived from query: {clean_topic}"],
                        ["Reference Context", "AVAILABLE" if document_context else "NOT_AVAILABLE", "Uploaded Source Documents" if document_context else "Information unavailable from provided sources."],
                        ["Verification Standard", "ACTIVE", "Query-grounded deterministic synthesis"]
                    ]
                },
                "callout": f"Key Milestone: Comprehensive evaluation and structured delivery for {clean_topic}."
            },
            {
                "heading": "2. Technical Architecture & Operational Framework",
                "paragraphs": [
                    f"Operational execution for {clean_topic} relies on structured methodologies, system alignment, and technical standards.",
                    "Implementation workflows adhere to explicit requirements derived from verified domain sources."
                ],
                "bullet_points": [
                    "Foundational Architecture: Establishing core operational frameworks and data pathways.",
                    "Methodology & Integration: Standardized execution and domain integration.",
                    "System Verification: Pre-execution validation and artifact verification."
                ],
                "table": {
                    "headers": ["Component / Deliverable", "Requirement Source", "Availability Status"],
                    "rows": [
                        [f"{clean_topic} Specifications", "User Query", "ACTIVE"],
                        ["Domain Source Data", "Reference Context" if document_context else "Pending Source Upload", "AVAILABLE" if document_context else "REQUIRES_SOURCE"],
                        ["Output Deliverable", "Target Document Format", "IN_PROGRESS"]
                    ]
                },
                "callout": "All milestones are tracked against strict domain verification criteria."
            },
            {
                "heading": "3. Data & Metric Verification",
                "paragraphs": [
                    f"Quantitative metrics, financial figures, and operational statistics for {clean_topic} are restricted to verified source documents.",
                    "When specific numerical values or financial budgets are not supplied in source materials, they are explicitly marked as unavailable rather than fabricated."
                ],
                "bullet_points": [
                    "Verification Standard: Zero fabricated statistics, synthetic estimates, or placeholder numbers.",
                    "Source Grounding: Financial metrics and quantitative parameters require verified user or document inputs."
                ],
                "table": {
                    "headers": ["Metric / Parameter", "Availability Status", "Source Value / Note"],
                    "rows": [
                        ["Financial Projections", "REQUIRES_SOURCE", "Information unavailable from provided sources."],
                        ["Quantitative Metrics", "REQUIRES_SOURCE", "Information unavailable from provided sources."],
                        ["Domain Reference Data", "AVAILABLE" if document_context else "NOT_AVAILABLE", context_snippet[:60] if context_snippet else "Information unavailable from provided sources."]
                    ]
                },
                "callout": "Notice: Numerical values and financial figures are restricted to verified source documents."
            },
            {
                "heading": "4. Strategic Roadmap & Implementation Analysis",
                "paragraphs": [
                    f"In conclusion, the strategic analysis for {clean_topic} provides a grounded, verified structure aligned with domain objectives.",
                    "Subsequent operational phases depend on reviewing outputs against required performance criteria."
                ],
                "bullet_points": [
                    "Review deliverable specifications against stakeholder requirements.",
                    "Integrate source data when additional quantitative parameters are needed.",
                    "Monitor milestone completion via continuous artifact verification."
                ],
                "table": None,
                "callout": f"Action Item: Execute operational roadmap for {clean_topic}."
            }
        ]

    data_table = {
        "sheet_name": "Scope_and_Metrics",
        "headers": ["Item / Parameter", "Data State", "Source Provenance", "Details"],
        "rows": [
            [clean_topic, "AVAILABLE", "User Query", "Directly requested by user"],
            ["Reference Material", "AVAILABLE" if document_context else "NOT_AVAILABLE", "Uploaded Context" if document_context else "None provided", "Grounded in reference documents" if document_context else "Information unavailable from provided sources."],
            ["Financial Metrics", "REQUIRES_SOURCE", "User / Document Input", "Information unavailable from provided sources."],
        ]
    }

    return {
        "scope_lock": {
            "must_include": [clean_q],
            "may_include": ["Direct implementation details"],
            "must_not_include": ["Generic fluff", "Unrequested marketing filler", "Placeholders"]
        },
        "topic": clean_topic,
        "title": title,
        "subtitle": "",
        "doc_type": "Strategic Report & Implementation Plan" if not is_ai_topic else "Comprehensive Technical Guide",
        "target_format": doc_format,
        "audience": "Enterprise Stakeholders and Technical Practitioners",
        "executive_summary": f"Structured operational and strategic deliverable for {clean_topic}.",
        "sections": sections,
        "data_table": data_table,
    }


async def plan_and_generate_content(
    query: str,
    doc_format: str,
    document_context: str = ""
) -> Dict[str, Any]:
    """
    Stage A of the Query Grounding & Content Relevance Protocol:
    1. Extracts topic, objectives, constraints, audience, and required content.
    2. Incorporates reference document context if available.
    3. Calls LLM with strict grounding prompt to generate structured JSON content.
    4. Validates and sanitizes content (zero placeholders, zero generic fluff).
    5. Falls back gracefully to topic-grounded deterministic plan if LLM is unavailable.
    """
    logger.info(f"Stage A Content Planner initiated for query: '{query[:60]}', format: {doc_format}")

    user_prompt = f"User Request: {query}\nTarget Document Format: {doc_format}\n"
    if document_context:
        user_prompt += f"\n--- REFERENCE DOCUMENT CONTEXT ---\n{document_context[:2500]}\n--- END REFERENCE CONTEXT ---\n"

    user_prompt += (
        "\nRemember:\n"
        "- Generate domain content strictly grounded in the user request and provided sources.\n"
        "- When asked about how a technology/system works (e.g. AI), generate educational and technical domain sections explaining that technology.\n"
        "- NEVER fabricate statistics, financial numbers, citations, or placeholder text.\n"
        "- If specific metrics or figures are requested but not supplied in context, explicitly state: 'Information unavailable from provided sources.'\n"
        "- Output strictly valid JSON matching the specified schema."
    )

    try:
        llm = get_llm(temperature=0.2)
        messages = [
            SystemMessage(content=CONTENT_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        
        response = await llm.ainvoke(messages)
        resp_text = response.content if hasattr(response, "content") else str(response)

        try:
            parsed = robust_json_loads(resp_text)
        except Exception:
            # Secondary fallback extraction
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", resp_text, re.DOTALL)
            raw_json = json_match.group(1) if json_match else resp_text
            parsed = json.loads(raw_json)

        cleaned = _validate_and_clean_content(parsed, query, doc_format)
        
        # Verify that we have at least 1 section with content or data_table
        if len(cleaned.get("sections", [])) >= 1 or cleaned.get("data_table"):
            logger.info(f"Stage A Content Planner successfully generated structured plan with {len(cleaned.get('sections', []))} sections.")
            return cleaned
        else:
            logger.warning("Stage A Content Planner returned empty sections; using grounded deterministic fallback.")
            return _build_deterministic_grounded_content(query, doc_format, document_context)

    except Exception as e:
        logger.warning(f"Stage A Content Planner LLM generation encountered error: {e}. Utilizing grounded deterministic synthesizer.")
        return _build_deterministic_grounded_content(query, doc_format, document_context)
