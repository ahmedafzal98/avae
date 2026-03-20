"""
Document compliance extraction: PDF → LlamaParse (Markdown) → LLM (structured JSON)
Usage: python test_document.py <path_to_pdf>
"""
import argparse
import os
import sys
import nest_asyncio
from pathlib import Path

# Apply nest_asyncio to prevent event loop crashes with LlamaParse
nest_asyncio.apply()

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

# Load .env from document-processor or current directory
_env_paths = [
    Path(__file__).resolve().parent / "document-processor" / ".env",
    Path(__file__).resolve().parent / ".env",
]
for _p in _env_paths:
    if _p.exists():
        load_dotenv(_p)
        break

# 1. Define the Rigid Schema specifically for the UK EPC Document
class EPCExtraction(BaseModel):
    reference_number: str = Field(description="The 20-digit RRN (Reference Number) formatted with dashes.")
    property_address: str = Field(description="The full address of the property being assessed.")
    current_energy_rating: str = Field(description="The current energy efficiency rating number (e.g., 49, 76, etc).")
    assessor_name: str = Field(description="The full name of the energy assessor.")
    assessor_accreditation_number: str = Field(description="The accreditation number of the assessor.")
    total_floor_area: str = Field(description="The total floor area including the unit of measurement (e.g., m2).")

def parse_pdf_with_llamaparse(pdf_path: str, tier: str = "cost_effective") -> str:
    """
    Parse PDF using LlamaParse and return Markdown.
    Requires LLAMA_CLOUD_API_KEY in environment.

    Tiers (per official docs - https://developers.llamaindex.ai/python/cloud/llamaparse/basics/tiers/):
    - fast: ~10k pages/min, basic text (1 credit/page)
    - cost_effective: balanced speed + accuracy, markdown (3 credits/page)
    - agentic: complex docs, ~100 pages/min (10 credits/page)
    - agentic_plus: max accuracy (45 credits/page)
    """
    api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise ValueError(
            "LLAMA_CLOUD_API_KEY not set. Add it to document-processor/.env or set the env var. "
            "Get a key from https://cloud.llamaindex.ai/api-key"
        )

    from llama_parse import LlamaParse

    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",
        verbose=True,
        language="en",
        # Performance: default is 4; num_workers=1 serializes requests (4x slower)
        num_workers=4,
        # Tier: cost_effective is faster than agentic; use --tier fast for max speed
        tier=tier,
        version="latest",
    )
    print(f"📄 Parsing PDF with LlamaParse (tier={tier}): {pdf_path}")
    documents = parser.load_data(pdf_path)
    texts = [doc.text for doc in documents if hasattr(doc, "text") and doc.text]
    markdown = "\n\n".join(texts)
    print(f"✅ Extracted {len(markdown)} chars from {len(documents)} document(s)")
    return markdown

def extract_markdown_from_pdf(pdf_path: str, tier: str = "cost_effective") -> str:
    """Extract Markdown from PDF using LlamaParse only."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path.suffix}")

    return parse_pdf_with_llamaparse(str(path), tier=tier)

def main():
    parser = argparse.ArgumentParser(description="Extract compliance entities from a PDF document")
    parser.add_argument("file", nargs="?", help="Path to PDF file")
    parser.add_argument("--markdown-only", action="store_true", help="Only output Markdown, skip LLM extraction")
    parser.add_argument(
        "--tier",
        choices=["fast", "cost_effective", "agentic", "agentic_plus"],
        default="cost_effective",
        help="LlamaParse tier: fast (fastest), cost_effective (default), agentic, agentic_plus (most accurate)",
    )
    args = parser.parse_args()

    if args.file:
        pdf_path = args.file
    else:
        pdf_path = input("Enter path to PDF file: ").strip()
        if not pdf_path:
            print("No file specified. Usage: python test_document.py <path_to_pdf>")
            sys.exit(1)

    # Step 1: Extract Markdown from PDF (LlamaParse only)
    markdown_from_llamaparse = extract_markdown_from_pdf(pdf_path, tier=args.tier)

    if args.markdown_only:
        print("\n--- EXTRACTED MARKDOWN ---")
        print(markdown_from_llamaparse)
        return

    # Step 2: Initialize LLM and extract structured data
    # NOTE: Ensure OPENAI_API_KEY is in your .env file
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(EPCExtraction)

    print("Extracting entities...")
    result = structured_llm.invoke(
        f"Extract the compliance entities from this document:\n\n{markdown_from_llamaparse}"
    )

    print("\n--- EXTRACTED JSON ---")
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    main()