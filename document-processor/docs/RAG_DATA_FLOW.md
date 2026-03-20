# 📊 RAG Data Flow - Visual Reference

## 🗄️ **Database Schema**

### **BEFORE RAG (What you had):**

```
┌──────────────────────────────────────────────────────────┐
│ documents table                                          │
├──────────────────────────────────────────────────────────┤
│ id          | user_id | filename      | s3_key | status  │
│-------------|---------|---------------|--------|---------|
│ 123         | 5       | contract.pdf  | s3://  | PENDING │
│ 124         | 5       | report.pdf    | s3://  | COMPLETED│
│ 125         | 8       | invoice.pdf   | s3://  | PROCESSING│
└──────────────────────────────────────────────────────────┘

Problem: ❌ No way to search document content by meaning
```

### **AFTER RAG (What you have now):**

```
┌──────────────────────────────────────────────────────────┐
│ documents table (unchanged - metadata only)              │
├──────────────────────────────────────────────────────────┤
│ id  | user_id | filename      | s3_key | status    | result_text │
│-----|---------|---------------|--------|-----------|-------------|
│ 123 | 5       | contract.pdf  | s3://  | COMPLETED | "Full text" │
└──────────────────────────────────────────────────────────┘
                              │
                              │ one-to-many
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ document_chunks table (NEW - RAG magic happens here) ⭐             │
├──────────────────────────────────────────────────────────────────────┤
│ id | doc_id | user_id | chunk_idx | text_content      | embedding    │
│----|--------|---------|-----------|-------------------|--------------|
│ 1  | 123    | 5       | 0         | "Chapter 1..."    | [0.1, 0.2...]│
│ 2  | 123    | 5       | 1         | "Section A..."    | [0.3, -0.1...]│
│ 3  | 123    | 5       | 2         | "The terms..."    | [-0.2, 0.4...]│
│ 4  | 123    | 5       | 3         | "Payment is..."   | [0.5, 0.1...]│
│... | ...    | ...     | ...       | ...               | ...          │
│ 50 | 123    | 5       | 49        | "Conclusion..."   | [0.2, -0.3...]│
└──────────────────────────────────────────────────────────────────────┘

Solution: ✅ Can now search by semantic similarity using embeddings
```

---

## 🔄 **Complete Data Flow**

### **PHASE 1: INGESTION (Implemented ✅)**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER UPLOADS PDF                                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. FASTAPI ENDPOINT                                             │
│    • Saves to S3                                                │
│    • Creates record in 'documents' table                        │
│    • Sends message to SQS queue                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. SQS WORKER RECEIVES TASK                                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. LLAMAPARSE EXTRACTION                                        │
│    • Downloads PDF from S3                                      │
│    • Sends to LlamaParse API                                    │
│    • Returns: Markdown text with tables preserved               │
│    • Example output: "# Chapter 1\n\nThe contract..."          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. RAG INGESTION STEP A: CHUNKING ⭐ NEW                        │
│    • Input: Full text (e.g., 50 pages = ~25,000 words)         │
│    • LlamaIndex SentenceSplitter:                               │
│      - chunk_size: 1024 tokens (~750 words)                     │
│      - chunk_overlap: 200 tokens (context preservation)         │
│    • Output: List of chunks                                     │
│      [                                                           │
│        {"text": "Chapter 1...", "index": 0},                    │
│        {"text": "Section A...", "index": 1},                    │
│        {"text": "The terms...", "index": 2},                    │
│        ...                                                       │
│      ]                                                           │
│    • Result: ~50 chunks for 50-page document                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. RAG INGESTION STEP B: EMBEDDING ⭐ NEW                       │
│    • Input: 50 chunk texts                                      │
│    • Calls OpenAI API:                                          │
│      POST https://api.openai.com/v1/embeddings                  │
│      {                                                           │
│        "model": "text-embedding-3-small",                       │
│        "input": ["Chapter 1...", "Section A...", ...]           │
│      }                                                           │
│    • Output: 50 embedding vectors                               │
│      [                                                           │
│        [0.123, -0.456, 0.789, ... ] (1536 numbers),            │
│        [0.234, 0.567, -0.123, ... ] (1536 numbers),            │
│        ...                                                       │
│      ]                                                           │
│    • Cost: ~$0.0007 for 50-page document                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. RAG INGESTION STEP C: STORAGE ⭐ NEW                         │
│    • Input: Chunks + Embeddings                                 │
│    • Inserts into 'document_chunks' table:                      │
│      INSERT INTO document_chunks VALUES                         │
│        (1, 123, 5, 0, "Chapter 1...", [0.123, -0.456, ...]),   │
│        (2, 123, 5, 1, "Section A...", [0.234, 0.567, ...]),    │
│        ...                                                       │
│    • Result: 50 rows in document_chunks                         │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. UPDATE DOCUMENT STATUS                                       │
│    • UPDATE documents SET status = 'COMPLETED'                  │
│    • User can now chat with this document!                      │
└─────────────────────────────────────────────────────────────────┘
```

---

### **PHASE 2: QUERY/CHAT (Coming Next 🔜)**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER ASKS QUESTION                                           │
│    "What are the payment terms in my contract?"                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. EMBED THE QUESTION                                           │
│    • Call OpenAI embedding API                                  │
│    • Input: "What are the payment terms in my contract?"        │
│    • Output: [0.145, -0.234, 0.567, ...] (1536 numbers)        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. VECTOR SIMILARITY SEARCH (pgvector)                          │
│    • SQL Query:                                                  │
│      SELECT text_content, embedding <=> question_embedding AS similarity │
│      FROM document_chunks                                       │
│      WHERE user_id = 5  -- User isolation                       │
│      ORDER BY embedding <=> question_embedding                  │
│      LIMIT 5;                                                   │
│                                                                  │
│    • Postgres calculates cosine similarity for all chunks       │
│    • Returns top 5 most similar chunks                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. RETRIEVED CHUNKS                                             │
│    [                                                             │
│      "Section 5: Payment terms are Net 30...",                  │
│      "The contract specifies payment within 30 days...",        │
│      "All invoices must be paid within 30 days...",             │
│      "Late payment fees: 2% per month...",                      │
│      "Payment method: Wire transfer or check..."                │
│    ]                                                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. BUILD PROMPT FOR LLM                                         │
│    System: You are a helpful assistant. Answer based on context.│
│                                                                  │
│    Context from documents:                                      │
│    ---                                                           │
│    Section 5: Payment terms are Net 30...                       │
│    The contract specifies payment within 30 days...             │
│    All invoices must be paid within 30 days...                  │
│    ---                                                           │
│                                                                  │
│    User Question: What are the payment terms in my contract?    │
│                                                                  │
│    Instructions: Answer based only on the context above.        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. CALL OPENAI CHAT API                                         │
│    • POST https://api.openai.com/v1/chat/completions           │
│    • Model: gpt-4 or gpt-3.5-turbo                             │
│    • Input: Full prompt with context + question                 │
│    • Output: AI-generated answer                                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. RETURN ANSWER TO USER                                        │
│    "Based on your contract, the payment terms are Net 30,      │
│     which means invoices must be paid within 30 days of         │
│     receipt. Late payments incur a 2% monthly fee."             │
│                                                                  │
│    Sources:                                                     │
│    • contract.pdf (page 5, chunk 12)                           │
│    • contract.pdf (page 6, chunk 15)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔢 **Example: Actual Data**

### **Document Record:**

```sql
SELECT * FROM documents WHERE id = 123;
```

| id  | user_id | filename      | status    | result_text           | page_count |
|-----|---------|---------------|-----------|----------------------|------------|
| 123 | 5       | contract.pdf  | COMPLETED | "# Service Agreement\n\nThis agreement..." | 50 |

### **Chunk Records:**

```sql
SELECT id, chunk_index, LEFT(text_content, 50) as preview, 
       array_length(embedding, 1) as emb_dim
FROM document_chunks 
WHERE document_id = 123 
LIMIT 5;
```

| id  | chunk_index | preview                                         | emb_dim |
|-----|-------------|-------------------------------------------------|---------|
| 1   | 0           | "# Service Agreement\n\nThis agreement entered..." | 1536    |
| 2   | 1           | "between ABC Corp (Client) and XYZ Inc..."      | 1536    |
| 3   | 2           | "Section 1: Scope of Work\n\nThe contractor..." | 1536    |
| 4   | 3           | "Section 2: Deliverables\n\n1. Design mockups..." | 1536    |
| 5   | 4           | "Section 3: Timeline\n\nPhase 1: Discovery..."  | 1536    |

### **Similarity Search Example:**

```sql
-- This is what happens when user asks: "What is the timeline?"
-- (query_embedding is the embedded question)

SELECT 
    id,
    chunk_index,
    LEFT(text_content, 60) as preview,
    1 - (embedding <=> '[0.123, -0.456, ...]'::vector) as similarity
FROM document_chunks
WHERE user_id = 5
ORDER BY embedding <=> '[0.123, -0.456, ...]'::vector
LIMIT 3;
```

**Results:**

| id  | chunk_index | preview                                           | similarity |
|-----|-------------|---------------------------------------------------|------------|
| 5   | 4           | "Section 3: Timeline\n\nPhase 1: Discovery..."   | 0.92       |
| 12  | 11          | "Project schedule: 6 months total..."            | 0.87       |
| 18  | 17          | "Milestones: Month 1-2: Design, Month 3-4..."    | 0.84       |

---

## 📐 **Understanding Embeddings**

### **What is an Embedding?**

An embedding is a numerical representation of text meaning.

```
Text: "The cat sat on the mat"
       ↓ (OpenAI embedding model)
Embedding: [0.234, -0.891, 0.456, 0.123, ..., 0.789]
           (1536 numbers between -1 and 1)
```

### **Why 1536 dimensions?**

- OpenAI's `text-embedding-3-small` model outputs 1536-dimensional vectors
- Each dimension captures a different semantic feature
- Higher dimensions = more nuanced meaning representation

### **Similarity Calculation:**

```
Question: "What is the payment policy?"
Question embedding: [0.2, 0.5, -0.3, ...]

Chunk 1: "Payment terms are Net 30"
Chunk 1 embedding: [0.19, 0.52, -0.31, ...]
→ Cosine similarity: 0.95 (very similar!)

Chunk 2: "The office is located in New York"
Chunk 2 embedding: [-0.4, 0.1, 0.7, ...]
→ Cosine similarity: 0.23 (not similar)

Result: Chunk 1 is retrieved, Chunk 2 is ignored
```

---

## 🎯 **Key Concepts Summary**

| Concept | Explanation |
|---------|-------------|
| **Chunk** | A small piece of text (~500-1000 words) split from the original document |
| **Embedding** | A list of 1536 numbers representing the meaning of text |
| **Vector Store** | A database (Postgres + pgvector) that stores embeddings and can search by similarity |
| **Cosine Similarity** | Math operation to measure how "close" two embeddings are (0 = different, 1 = identical) |
| **Multi-Tenancy** | User isolation: Each user only sees their own document chunks via `user_id` filtering |
| **RAG** | Retrieval-Augmented Generation: Retrieve relevant chunks, then generate answer with LLM |

---

## 🔗 **API Calls Summary**

### **During Ingestion (per document):**

1. **LlamaParse API:**
   - Endpoint: LlamaCloud
   - Purpose: Extract text from PDF
   - Cost: ~5-10 credits per page

2. **OpenAI Embeddings API:**
   - Endpoint: `https://api.openai.com/v1/embeddings`
   - Purpose: Convert chunks to vectors
   - Calls: 1 batch call (for all chunks)
   - Cost: ~$0.0007 per 50-page document

### **During Query (per question):**

1. **OpenAI Embeddings API:**
   - Purpose: Convert question to vector
   - Calls: 1
   - Cost: ~$0.000001

2. **OpenAI Chat API:**
   - Endpoint: `https://api.openai.com/v1/chat/completions`
   - Purpose: Generate answer from retrieved chunks
   - Calls: 1
   - Cost: ~$0.001-0.01 per query (depending on model)

---

## ✅ **Current Status**

| Feature | Status |
|---------|--------|
| Document Upload | ✅ Working (existing) |
| LlamaParse Extraction | ✅ Working (existing) |
| Text Chunking | ✅ **NEW - Phase 1** |
| Embedding Generation | ✅ **NEW - Phase 1** |
| Vector Storage | ✅ **NEW - Phase 1** |
| Multi-Tenancy | ✅ **NEW - Phase 1** |
| Chat Endpoint | 🔜 Phase 2 |
| Vector Search | 🔜 Phase 2 |
| LLM Answer Generation | 🔜 Phase 2 |

---

**You're now ready to move to Phase 2: Implementing the chat/query functionality!** 🚀
