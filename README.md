# RAG Chat App

A ChatGPT-style RAG application built with Python + Streamlit.

## Features

- ChatGPT-like full-page chat UI
- Left sidebar containing persistent chat history
- New chat
- Persistent conversations in SQLite
- PDF / TXT / Markdown / DOCX ingestion
- Chunking with overlap
- Azure OpenAI embeddings
- Chroma persistent vector store
- Top-K semantic retrieval
- Azure OpenAI answer generation
- Source display for every RAG answer
- Conversation context included in the generation prompt

## Architecture

Streamlit UI
    |
    +-- SQLite -----------------> Chat history
    |
    +-- RAGEngine
          |
          +-- Document parser
          +-- Chunker
          +-- Azure OpenAI embeddings
          +-- ChromaDB
          +-- Top-K retrieval
          +-- Azure OpenAI chat completion

## Setup

### 1. Create environment

Windows:

    python -m venv .venv
    .venv\Scripts\activate

Linux/macOS:

    python -m venv .venv
    source .venv/bin/activate

### 2. Install dependencies

    pip install -r requirements.txt

### 3. Configure Azure OpenAI

Copy `.env.example` to `.env` and fill in:

    AZURE_OPENAI_ENDPOINT=
    AZURE_OPENAI_API_KEY=
    AZURE_OPENAI_API_VERSION=
    AZURE_OPENAI_CHAT_DEPLOYMENT=
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT=

The deployment values must be the deployment names configured in your Azure OpenAI resource.

### 4. Run

    streamlit run app.py

Then open the local URL shown by Streamlit.

## Recommended production improvements

This project is intentionally a clean starter implementation. For production, consider:

- Hybrid search: vector + BM25
- Reranking after retrieval
- Parent-child / hierarchical chunks
- Metadata filters such as tenant, document, page and ACL
- Streaming model output
- Async ingestion pipeline
- Background document processing
- Blob/object storage instead of local files
- PostgreSQL/Azure SQL instead of SQLite
- Authentication and per-user chat isolation
- Token-aware conversation summarization
- Evaluation using retrieval and answer quality metrics
- Observability/tracing
- Prompt/version management
- Multi-provider LLM abstraction
