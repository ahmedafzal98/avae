# Extraction Strategy for Unpredictable Document Structures

**Deep research summary and recommended approach for AVAE**

---

## The Problem

- Users upload PDFs of unknown structure
- Pre-defined schemas (EPC, Companies House, Land Registry) may not fit
- Users may need custom fields that don't exist in our models
- We need both: **structured output for API verification** (known targets) and **flexibility for unknown docs**

---

## Research Findings

### 1. Root Cause of Extraction Failures (Reducto, Tensorlake)

> **Extraction failures are often caused by parsing, not extraction.**

- If the value isn't in the parsed text, no schema will help
- **Implication:** Improve text extraction (LlamaParse, OCR) first; schema design second
- **Decoupling:** Parse once → cache text → run multiple extraction schemas without re-parsing

### 2. Schema Design Principles (Reducto, Microsoft)

| Principle | Why |
|-----------|-----|
| **Descriptive field names** | LLM uses names as search hints; `po_number` matches "PO Number" in doc |
| **Descriptions that locate values** | Tell model *where* to look and *what distinguishes* this field from similar ones |
| **Constrain with enums** | Prevents hallucination; forces canonical format (e.g. "paid" vs "PAID" vs "Paid") |
| **Keep nesting shallow** | Deep nesting reduces accuracy; flatten and restructure in code |
| **Extract only what exists** | No calculated fields; no inferred data; extract raw, transform yourself |

### 3. Two-Phase Architecture (Tensorlake, Docupipe)

```
Phase 1: Parse/OCR  →  Text (Markdown)
Phase 2: Extract    →  Structured JSON (schema-driven)
```

**Benefits:**
- One parse pass serves multiple schemas
- Schema iteration without re-parsing (cost, latency)
- Cleaner evaluation (measure schema changes, not parse variance)
- A/B test extraction logic on identical inputs

**AVAE already does this:** Text extracted once (legacy/LlamaParse) → passed to `extract_structured`.

### 4. Dynamic Schema Approaches

| Approach | Source | Use Case |
|----------|--------|----------|
| **JSON Schema at runtime** | OpenAI, LangChain | User-defined schema; `with_structured_output` accepts JSON Schema dict |
| **Pydantic `create_model()`** | Pydantic | Build model from field list at runtime |
| **Zero-shot discovery (ZOES)** | arXiv 2025 | Infer entity structure without predefined schema |
| **Schema inference on-the-fly** | LlamaIndex DynamicLLMPathExtractor | Detect entity types, expand ontology |
| **Automated schema generation** | Google Doc AI | Generate schema from sample docs; user approves/edits |
| **PARSE (schema optimization)** | arXiv 2024 | LLM refines schema for better extraction; 64.7% accuracy gain |

### 5. Enterprise Patterns (Google Doc AI, Reducto)

- **Custom extractors:** User-defined entity schema (up to ~150 entities)
- **Three training modes:** Foundation (0–50 docs), Custom (10–100 docs), Template (3 docs)
- **Confidence scoring:** Threshold for manual review of low-confidence extractions
- **Citations:** Link extracted values to source locations for audit/debug

### 6. OpenAI Structured Outputs (2024)

- `strict: true` + JSON Schema → **100% schema adherence** (gpt-4o-2024-08-06)
- Eliminates parsing errors, retries, validation
- LangChain `with_structured_output` supports: Pydantic, JSON Schema dict, TypedDict

---

## Recommended Strategy: Tiered Extraction

### Tier 1 — Known Compliance Targets (Current)

**When:** `audit_target` ∈ {epc, companies_house, hm_land_registry}

**Schema:** Fixed Pydantic models in `schemas_extraction.py`

**Purpose:** API verification (Phase 2); strict structure required

**No change needed.**

---

### Tier 2 — User-Defined Custom Schema

**When:** `audit_target=custom` AND user provides `extraction_fields` or `extraction_schema`

**Schema:** Built at runtime from user input

**Implementation options:**

| Option | Input | Output | Pros | Cons |
|--------|-------|--------|------|------|
| **A. Field list** | `["invoice_no", "vendor", "total"]` | Flat dict | Simple, no schema storage | All strings, no types |
| **B. JSON Schema** | `{"properties": {"invoice_no": {"type": "string", "description": "..."}}}` | Validated dict | Full control, types, descriptions | More complex API |
| **C. Pydantic `create_model`** | Field list + optional types | Pydantic instance | Type-safe, works with `with_structured_output` | Limited to flat structures |

**Recommendation:** Start with **Option A** (field list) for MVP; add **Option B** (JSON Schema) when users need types/descriptions.

```python
# Option A: Field list → dynamic Pydantic
from pydantic import create_model, Field

def build_schema_from_fields(fields: list[str]) -> type[BaseModel]:
    return create_model(
        "CustomExtraction",
        **{f: (str, Field(description=f"Extract the value for {f} from the document")) for f in fields}
    )
```

---

### Tier 3 — Discovery-First (Optional, Future)

**When:** Truly unknown document; user wants "extract whatever you find"

**Flow:**
1. **Discovery pass:** LLM extracts key-value pairs (free-form) or infers entity types
2. **Optional:** User reviews/edits discovered schema
3. **Extraction pass:** Re-run with refined schema (text already cached)

**Schema:** Generic `List[{"field": str, "value": str}]` or inferred schema from discovery

**Use case:** Exploratory compliance; new document types before schema is defined

---

## Architecture Recommendations

### 1. Decouple Parse from Extract (Already Done)

- Text extracted once in worker
- Store `result_text` in `documents` table
- **Future:** Allow re-extraction with different schema without re-downloading/re-parsing PDF

### 2. Schema Storage

- **Known targets:** In code (`schemas_extraction.py`)
- **Custom schemas:** Store in DB or pass at upload
- **Discovery results:** Store in `audit_logs.extracted_json` with `schema_used: "discovery"`

### 3. Hybrid Schema (Known + Extra)

Add `extra_fields: dict[str, str]` to fixed schemas:

```python
class EPCExtraction(BaseModel):
    reference_number: str = ...
    # ... required fields
    extra_fields: dict[str, str] = Field(default_factory=dict, description="Any other relevant entities found")
```

- Core fields stay structured for API verification
- Unknown-but-useful data captured in `extra_fields`

### 4. Improve Schema Descriptions

Apply Reducto principles to existing schemas:

```python
# Before
reference_number: str = Field(description="The RRN")

# After
reference_number: str = Field(
    description="The 20-digit RRN (Reference Number), typically formatted with dashes (e.g. 1234-5678-9012-3456-7890), found in the certificate header"
)
```

### 5. Re-Extraction Without Re-Parse

When user changes schema or adds custom fields:

- Fetch `result_text` from `documents`
- Call `extract_structured(text, audit_target, custom_schema=...)`
- Insert new `audit_log` row (or update)
- No S3 download, no PDF parsing

---

## Implementation Roadmap

| Phase | Scope | Effort |
|-------|-------|--------|
| **Now** | Tier 1 (current) | Done |
| **Phase 1.5** | Add `custom` audit_target + field list | 1–2 days |
| **Phase 1.6** | Improve schema descriptions (Reducto principles) | 0.5 day |
| **Phase 2** | Re-extraction API (schema change without re-parse) | 1 day |
| **Future** | Tier 3 discovery; JSON Schema input | 2–3 days |

---

## Summary: Best Strategy

1. **Keep Tier 1** for known compliance targets (API verification).
2. **Add Tier 2** with `audit_target=custom` + `extraction_fields: list[str]` for user-defined extraction.
3. **Improve schema design** with descriptive names and location-focused descriptions.
4. **Add `extra_fields`** to fixed schemas to capture unexpected but useful data.
5. **Decouple re-extraction** so schema changes don't require re-parsing.
6. **Consider Tier 3** (discovery) only when users need exploratory extraction.

---

## References

- Reducto: [Extract Best Practices](https://docs.reducto.ai/extraction/best-practices-extract)
- Tensorlake: [Decoupling OCR from Structured Extraction](https://www.tensorlake.ai/blog/decouple-ocr-structured-extraction)
- OpenAI: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- LangChain: [Structured Output](https://python.langchain.com/docs/how_to/structured_output)
- Google Doc AI: [Custom Extractor](https://docs.cloud.google.com/document-ai/docs/custom-extractor-overview)
- PARSE: [LLM Driven Schema Optimization](https://arxiv.org/html/2510.08623v1)
- ZOES: [Zero-Shot Open-Schema Entity Structure Discovery](https://arxiv.org/pdf/2506.04458)
