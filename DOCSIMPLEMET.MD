# Implement Missing Components of the Intelligent Document Generation Agent

You have already implemented the core **Intelligent Document Generation Agent** with:

* `SKILL.md` master specification
* Scope Lock
* Query grounding
* Content planning
* Stage A content planning
* Stage B Sandbox execution
* DOCX/XLSX/PPTX deterministic generation
* FilesystemBackend final artifact storage
* Placeholder sanitization
* Document grounding tests
* 7/7 existing tests passing

**Do NOT rewrite or destabilize the existing working implementation.**

Your task is to **extend the existing system into the complete stateful, asynchronous, fault-tolerant Intelligent Document Generation Agent architecture** described below.

---

# 1. NON-NEGOTIABLE PRINCIPLES

Preserve these principles throughout the implementation:

### User decides WHAT

The user's request is the source of truth for document content.

### Skills decide HOW

Installed skills determine how DOCX, PPTX, XLSX, PDF, etc. are generated and formatted.

### Orchestrator controls the WORKFLOW

The orchestrator decides:

* planning
* task decomposition
* agent execution
* integration
* validation
* repair
* sandbox execution
* artifact delivery

### Never expand user scope

Do NOT add:

* generic introductions
* generic conclusions
* marketing content
* unrelated sections
* unnecessary explanations
* invented facts
* filler
* placeholder content

unless explicitly requested or required by the selected skill for technical reasons.

---

# 2. DO NOT BREAK EXISTING FUNCTIONALITY

Before modifying anything:

1. Inspect the current repository.
2. Identify the existing document-generation flow.
3. Identify `content_planner.py`.
4. Identify the current skill loader/registry.
5. Identify Sandbox implementation.
6. Identify FilesystemBackend implementation.
7. Identify existing StateBackend implementation, if any.
8. Run the existing test suite.

The current 7 tests in:

```text
test_document_grounding.py
```

must continue to pass.

Do not replace working deterministic generation with an unnecessarily complex implementation.

Use the existing implementation as the foundation.

---

# 3. IMPLEMENT STATEBACKEND

Integrate **StateBackend** as the lightweight workflow state layer.

Do NOT store large files, PDFs, images, DOCX, PPTX, XLSX, or other binaries in StateBackend.

StateBackend should contain only task/workflow state.

Create a structured state model similar to:

```text
DocumentGenerationState
├── task_id
├── user_id
├── original_query
├── query_analysis
├── scope_lock
├── selected_skills
├── document_type
├── document_plan
├── tasks
├── task_status
├── subagent_status
├── generated_sections
├── integration_status
├── validation_results
├── repair_tasks
├── sandbox_status
├── file_validation_status
├── artifact_metadata
├── error
└── overall_status
```

Use StateBackend for:

* query analysis
* scope lock
* plan
* task decomposition
* task status
* sub-agent status
* validation state
* repair state
* generation state
* final artifact metadata

Do NOT put actual document binaries into StateBackend.

---

# 4. IMPLEMENT TASK LIFECYCLE

Introduce explicit task states:

```text
CREATED
ANALYZING
PLANNING
SKILL_SELECTION
DECOMPOSING
GENERATING
INTEGRATING
VALIDATING
REPAIRING
SANDBOX_RUNNING
FILE_VALIDATING
COMPLETED
FAILED
CANCELLED
TIMEOUT
```

Every state transition should be persisted.

Example:

```text
CREATED
  ↓
ANALYZING
  ↓
PLANNING
  ↓
SKILL_SELECTION
  ↓
DECOMPOSING
  ↓
GENERATING
  ↓
VALIDATING
  ↓
SANDBOX_RUNNING
  ↓
FILE_VALIDATING
  ↓
COMPLETED
```

If an error occurs, persist:

```text
status = FAILED
error = ...
```

Do not silently swallow errors.

---

# 5. IMPLEMENT COMPLEXITY ANALYZER

Add a lightweight task complexity analyzer.

The system must determine whether the request is:

```text
SMALL
MEDIUM
LARGE
```

Consider:

* requested document length
* number of sections
* number of source documents
* number of independent sections
* tables/charts required
* research requirements
* multimodal requirements
* expected generation time
* dependencies between sections

Example:

```text
Small task
→ Primary Agent

Large task
→ Task decomposition
→ Async content sub-agents
```

Do not create sub-agents for trivial documents.

Avoid one-agent-per-page.

Prefer logical work units:

```text
Executive Summary
Technical Analysis
Financial Analysis
Risk Analysis
Appendix
```

rather than:

```text
Page 1 agent
Page 2 agent
Page 3 agent
...
```

---

# 6. IMPLEMENT TASK DECOMPOSITION

For complex documents, convert the document plan into executable tasks.

Each task should contain:

```text
task_id
section_id
title
objective
requirements
scope_constraints
dependencies
required_skills
source_material
status
```

Example:

```json
{
  "task_id": "section_03",
  "section_id": "technical_analysis",
  "objective": "Explain the requested technical architecture",
  "requirements": [],
  "scope_constraints": [],
  "dependencies": [],
  "required_skills": ["document-processing"],
  "status": "PENDING"
}
```

The decomposition must remain strictly inside the Scope Lock.

---

# 7. IMPLEMENT ASYNC CONTENT SUB-AGENTS

For large/complex tasks, generate independent sections using asynchronous sub-agents.

The orchestrator remains the authority.

Sub-agents must NOT:

* redefine scope
* add sections
* change document type
* invent requirements
* modify other sections
* execute final document formatting
* bypass validation

Each sub-agent receives:

```text
Original User Query
Scope Lock
Document Plan
Selected Skill Instructions
Assigned Section
Section Requirements
Relevant Source Material
Tone
Detail Level
Dependencies
```

Each sub-agent returns structured output:

```json
{
  "task_id": "...",
  "section_id": "...",
  "status": "COMPLETED",
  "content": "...",
  "sources_used": [],
  "warnings": [],
  "missing_information": [],
  "validation_notes": []
}
```

Use async execution only when tasks are sufficiently independent.

Tasks with dependencies must wait for their dependencies.

---

# 8. IMPLEMENT SUB-AGENT FAILURE HANDLING

If one section fails:

```text
Section A → SUCCESS
Section B → SUCCESS
Section C → FAILED
Section D → SUCCESS
```

Do NOT regenerate A, B, and D.

Retry only C.

Implement:

```text
retry_count
max_retries
failure_reason
```

After the retry limit is reached:

```text
task.status = FAILED
document.status = FAILED
```

unless the failed section is explicitly optional according to the plan.

---

# 9. IMPLEMENT CONTENT INTEGRATOR

Create a dedicated content integration step.

Input:

```text
Generated Section Results
```

Output:

```text
Integrated Document Content
```

The integrator must:

* preserve Scope Lock
* preserve document plan
* remove duplicate content
* normalize terminology
* normalize tone
* maintain section ordering
* resolve obvious cross-section inconsistencies
* preserve required facts
* preserve source references
* avoid adding new scope

Critical rule:

> Integration may reorganize existing generated content but must NOT invent new requirements or expand the document.

---

# 10. IMPLEMENT SEMANTIC CONTENT VALIDATOR

Create a validator that runs **before Sandbox execution**.

Validate:

### Scope

Does the document contain only requested content?

### Completeness

Are all `MUST INCLUDE` requirements present?

### Forbidden content

Are any `MUST NOT INCLUDE` items present?

### Grounding

Are factual claims supported by available source material?

### Structure

Does the generated content follow the document plan?

### Consistency

Are terminology, numbers, names, and claims consistent?

### Placeholders

Reject:

```text
TODO
TBD
Lorem ipsum
[Insert ...]
<placeholder>
```

### Relevance

Remove or flag unnecessary content.

Return structured results:

```json
{
  "valid": false,
  "issues": [
    {
      "type": "SCOPE_VIOLATION",
      "section_id": "section_03",
      "message": "Unrequested market analysis was added"
    }
  ]
}
```

---

# 11. IMPLEMENT TARGETED REPAIR

Do NOT regenerate the entire document when validation fails.

Use:

```text
Generate
 ↓
Validate
 ↓
PASS → Sandbox
 ↓
FAIL
 ↓
Identify affected section
 ↓
Create repair task
 ↓
Regenerate ONLY affected section
 ↓
Integrate
 ↓
Validate again
```

Example:

```text
Section 1 → PASS
Section 2 → PASS
Section 3 → FAIL
Section 4 → PASS
```

Only regenerate:

```text
Section 3
```

Track:

```text
repair_count
repair_reason
previous_validation_result
repair_result
```

Set a maximum repair limit to prevent infinite loops.

---

# 12. IMPLEMENT DYNAMIC SKILL DISCOVERY

Do not rely only on hardcoded document-type mappings.

The system should:

1. Discover installed skills.
2. Read relevant `SKILL.md` files.
3. Determine which skills apply.
4. Select the required skills.
5. Pass their instructions into the appropriate generation stage.

Example:

```text
User:
Create an Excel financial analysis.

Skill discovery:

xlsx
excel-analysis
```

For:

```text
Create a technical PDF from scanned documents.
```

Potentially:

```text
pdf-processing
pdf-processing-pro
document-processing
OCR/vision skill
```

Do not load every installed skill unnecessarily.

Select only relevant skills.

---

# 13. IMPLEMENT SOURCE PROVENANCE

For grounded documents, track where important factual claims originated.

Represent claims approximately as:

```json
{
  "claim": "...",
  "source": "annual_report.pdf",
  "location": "page 42",
  "confidence": 0.98
}
```

Do not invent source locations.

If provenance is unavailable, mark the claim appropriately rather than fabricating citation information.

Use provenance internally even when the final document does not require visible citations.

---

# 14. IMPLEMENT RESUME / RECOVERY

The system must be able to recover a long-running task from StateBackend.

Example:

```text
Section 1 → COMPLETED
Section 2 → COMPLETED
Section 3 → COMPLETED
Section 4 → FAILED
Section 5 → COMPLETED
```

After process restart:

```text
Load task state
        ↓
Skip completed tasks
        ↓
Retry Section 4
        ↓
Continue workflow
```

Never regenerate completed sections unnecessarily.

---

# 15. FILESYSTEMBACKEND RESPONSIBILITY

Keep actual files in FilesystemBackend.

Recommended structure:

```text
/workspace/users/{user_id}/generated/{task_id}/

    source/
    assets/
    intermediate/
    output/
        final_document.ext
```

StateBackend stores metadata.

FilesystemBackend stores actual artifacts.

Example:

```text
StateBackend
→ artifact_path = /workspace/users/.../final_document.docx

FilesystemBackend
→ actual final_document.docx
```

---

# 16. IMPLEMENT FINAL ARTIFACT VALIDATION

After Sandbox generation, validate the actual file.

For DOCX:

* file exists
* readable
* valid ZIP/XML structure
* expected sections exist
* no placeholder text

For XLSX:

* workbook opens
* worksheets exist
* expected data exists
* formulas are valid where applicable

For PPTX:

* presentation opens
* expected slide count
* expected slide content exists
* no empty required slides

For PDF:

* file opens
* expected page count
* extracted text is present
* no obvious corruption

Do not declare success until final file validation passes.

---

# 17. ARTIFACT METADATA

Store final artifact metadata in StateBackend:

```json
{
  "artifact": {
    "filename": "report.docx",
    "path": "/workspace/users/.../generated/report.docx",
    "type": "docx",
    "size": 123456,
    "validated": true,
    "created_at": "...",
    "task_id": "..."
  }
}
```

The actual file remains in FilesystemBackend.

---

# 18. ORCHESTRATOR

Create or update the main orchestrator so the workflow becomes:

```text
USER QUERY
    ↓
QUERY ANALYSIS
    ↓
SCOPE LOCK
    ↓
SKILL DISCOVERY
    ↓
DOCUMENT PLAN
    ↓
STATEBACKEND CHECKPOINT
    ↓
COMPLEXITY ANALYSIS
    ↓
TASK DECOMPOSITION
    ↓
 ┌────────────────────────────┐
 │                            │
 SMALL                       LARGE
 │                            │
 Primary Agent          Async Sub-Agents
 │                            │
 └──────────────┬─────────────┘
                ↓
       CONTENT INTEGRATION
                ↓
       SEMANTIC VALIDATION
                ↓
       ┌────────┴────────┐
       │                 │
     PASS               FAIL
       │                 │
       ↓                 ↓
    SANDBOX        TARGETED REPAIR
       │                 │
       │            RE-INTEGRATE
       │                 │
       │            RE-VALIDATE
       │                 │
       └────────┬────────┘
                ↓
        FILE VALIDATION
                ↓
       FILESYSTEMBACKEND
                ↓
        FINAL ARTIFACT
                ↓
        USER DELIVERY
```

---

# 19. OBSERVABILITY

For each task maintain:

```text
task_id
status
started_at
completed_at
duration
current_stage
retry_count
validation_attempts
subagent_count
errors
artifact_path
```

Do not expose internal chain-of-thought.

Expose only safe operational information such as:

```text
Planning document...
Generating sections...
Validating content...
Generating final DOCX...
Document validated successfully.
```

---

# 20. TESTS TO ADD

Keep all existing 7 tests.

Add tests for:

### StateBackend

```text
test_state_persistence
test_state_resume
test_state_transition
```

### Complexity

```text
test_small_task_uses_primary_agent
test_large_task_uses_async_agents
```

### Task decomposition

```text
test_task_decomposition_respects_scope
test_dependencies_are_preserved
```

### Async generation

```text
test_parallel_section_generation
test_failed_section_retry
```

### Integration

```text
test_content_integration
test_duplicate_removal
test_scope_preservation_after_integration
```

### Validation

```text
test_semantic_scope_validation
test_missing_required_section
test_forbidden_content_detection
test_placeholder_detection
test_grounding_validation
```

### Targeted repair

```text
test_only_failed_section_is_repaired
test_repair_limit
```

### Artifact validation

```text
test_docx_artifact_validation
test_xlsx_artifact_validation
test_pptx_artifact_validation
test_pdf_artifact_validation
```

### Recovery

```text
test_resume_after_process_restart
test_completed_tasks_are_not_regenerated
```

---

# 21. BACKWARD COMPATIBILITY

The existing deterministic fallback generation must remain functional.

Do not remove:

```text
build_fallback_document_docx
build_fallback_document_xlsx
build_fallback_document_pptx
```

unless you have a strictly compatible replacement and all tests continue passing.

Existing behavior should become the fallback path:

```text
Advanced Agent Workflow
        ↓
if successful
        ↓
Sandbox Generation

if advanced workflow unavailable
        ↓
Existing deterministic generation
```

Do not silently downgrade when doing so would violate the user's requested content.

---

# 22. IMPLEMENTATION ORDER

Implement in this order:

### Phase 1

```text
StateBackend
Task State
Task Lifecycle
```

### Phase 2

```text
Complexity Analyzer
Task Decomposition
```

### Phase 3

```text
Async Content Sub-Agents
Sub-agent Status Tracking
Retry Handling
```

### Phase 4

```text
Content Integrator
Semantic Validator
Targeted Repair
```

### Phase 5

```text
Dynamic Skill Discovery
Source Provenance
```

### Phase 6

```text
Resume/Recovery
Final Artifact Validation
Observability
```

### Phase 7

```text
Complete test suite
Regression testing
```

---

# 23. IMPORTANT ANTI-OVERENGINEERING RULE

Do NOT introduce async sub-agents, complex orchestration, or additional processing for every document.

Use the simplest workflow that satisfies the request.

For example:

```text
"Create a 1-page DOCX containing these 5 bullet points."
```

should remain:

```text
Query
 ↓
Scope Lock
 ↓
Plan
 ↓
Generate
 ↓
Sandbox
 ↓
Validate
 ↓
Artifact
```

Not:

```text
Query
 ↓
5 sub-agents
 ↓
integration
 ↓
repair
 ↓
multiple validation loops
```

The architecture must scale **up when complexity requires it**, not add unnecessary overhead.

---

# 24. FINAL ACCEPTANCE CRITERIA

The implementation is complete only when:

* Existing 7/7 tests still pass.
* StateBackend is actively used for workflow state.
* FilesystemBackend stores actual files/artifacts.
* Task lifecycle is persisted.
* Small tasks can use the primary agent directly.
* Large tasks can be decomposed.
* Independent sections can run asynchronously.
* Sub-agent failures can be retried independently.
* Content can be integrated without scope expansion.
* Semantic validation happens before Sandbox execution.
* Failed sections can be repaired individually.
* Skills can be discovered/selected appropriately.
* Source provenance can be tracked when grounding is used.
* Long-running tasks can resume after interruption.
* Final artifacts are technically validated.
* Final artifact metadata is stored in StateBackend.
* No unnecessary content is introduced.
* No user-requested content is silently removed.
* No placeholder content remains.
* No fabricated facts or citations are introduced.
* The existing deterministic generation path remains compatible.

---

# FINAL GOLDEN RULE

The system must always follow:

```text
USER
  ↓
WHAT?
  ↓
SCOPE LOCK
  ↓
PLAN
  ↓
SKILLS
  ↓
HOW?
  ↓
GENERATE
  ↓
VALIDATE
  ↓
REPAIR ONLY WHAT FAILED
  ↓
SANDBOX
  ↓
FINAL ARTIFACT
```

**The agent should never confuse "being intelligent" with adding more content.**

The objective is:

> **Generate exactly what the user requested, using the appropriate skills, with persistent state, scalable execution, validation, and reliable artifact delivery.**
