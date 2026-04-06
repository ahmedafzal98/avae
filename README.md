# AVAE — Agentic Verification and Audit Engine

Enterprise document verification for UK compliance. Extract structured data from PDFs, verify against official sources (Companies House, EPC, Land Registry), and maintain a full audit trail with human-in-the-loop resolution.

---

## Quick Start (Mac)

```bash
./setup.sh      # First-time setup (Docker, deps, env)

# Edit .env files with your API keys, then:
./start-dev.sh  # Start the app
```

- **Next.js:** http://localhost:3000  
- **FastAPI:** http://localhost:8000  
- **API docs:** http://localhost:8000/docs  

**Demo PDFs (Vision POC):** see [`document-processor/samples/demo/`](document-processor/samples/demo/README.md) — includes `Eng-Arabic.pdf` and `809508119-Iqama.pdf`. Run `document-processor/scripts/upload_demo_pdfs.sh` after the API is up.

---

## Full Setup Guide

See **[SETUP.md](./SETUP.md)** for:

- Prerequisites (Docker, Python 3.11+, Node 18+)
- Manual setup steps
- Environment variables
- Troubleshooting

---

## Project Structure

```
├── document-processor/   # FastAPI backend, SQS worker, LangGraph pipeline
├── frontend/             # Next.js UI (AVAE dashboard)
├── setup.sh              # One-command setup
├── start-dev.sh          # Start all services
└── SETUP.md              # Detailed setup guide
```

---

## License

MIT
