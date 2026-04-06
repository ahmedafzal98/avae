# Demo sample PDFs

These files are checked in for **Vision POC** demos (GPT-4o multimodal extraction). Use **`audit_target=vision_poc`** at upload and ensure the **SQS worker** is running so processing completes.

| File | Description |
|------|-------------|
| **Eng-Arabic.pdf** | English / Arabic mixed document — exercises RTL, mixed script, and layout. |
| **809508119-Iqama.pdf** | Saudi residence permit (Iqama)–style card — image-heavy; relies on vision + OCR fallbacks. |

## Quick upload (local API)

From `document-processor/`:

```bash
./scripts/upload_demo_pdfs.sh
```

Or with curl:

```bash
curl -sS -X POST "http://localhost:8000/upload?audit_target=vision_poc&user_id=1" \
  -F "files=@samples/demo/Eng-Arabic.pdf" \
  -F "files=@samples/demo/809508119-Iqama.pdf"
```

Then open **Verification** → **Completed extractions** (or **Audit Log**) and select the document to review PDF + extracted fields.
