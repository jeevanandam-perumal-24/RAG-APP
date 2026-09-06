import os
import re
from pathlib import Path
from typing import List, Dict

import chromadb
import requests
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from openai import AzureOpenAI
from pypdf import PdfReader
from docx import Document

load_dotenv()

DATA_DIR = Path("data")
CHROMA_DIR = Path("chroma_db")
DATA_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

class RAGEngine:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.open_router_chat_completion_api_key = os.getenv("OPEN_ROUTER_CHAT_COMPLETION_API_KEY", "")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
        self.chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "")
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "")
        self.top_k = int(os.getenv("RAG_TOP_K", "5"))
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "900"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "150"))
        self.gemini_embedding_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))

        self.is_configured = all([
            self.endpoint,
            self.api_key,
            self.chat_deployment,
            self.embedding_deployment,
        ])

        self.client = None
        if self.is_configured:
            self.client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )

        self.chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = self.chroma.get_or_create_collection(
            name="rag_documents",
            metadata={"hnsw:space": "cosine"},
        )

    def _embed(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            result = self.gemini_embedding_client.models.embed_content(
                        model="gemini-embedding-001",
                        contents=text,
                        config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
                    )
            embeddings.append(result.embeddings[0].values)
        return embeddings

    def _extract_text(self, filename: str, raw: bytes) -> str:
        suffix = Path(filename).suffix.lower()

        if suffix == ".pdf":
            temp = DATA_DIR / filename
            temp.write_bytes(raw)
            reader = PdfReader(str(temp))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)

        if suffix == ".docx":
            temp = DATA_DIR / filename
            temp.write_bytes(raw)
            doc = Document(str(temp))
            return "\n".join(p.text for p in doc.paragraphs)

        return raw.decode("utf-8", errors="ignore")

    def _chunk(self, text: str) -> List[str]:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        chunks = []
        start = 0
        while start < len(text):
            end = min(len(text), start + self.chunk_size)

            if end < len(text):
                boundary = max(
                    text.rfind(". ", start, end),
                    text.rfind("\n", start, end),
                    text.rfind(" ", start, end),
                )
                if boundary > start + int(self.chunk_size * 0.55):
                    end = boundary + 1

            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(0, end - self.chunk_overlap)

        return [c for c in chunks if c]

    def ingest_file(self, uploaded_file) -> int:
        if not self.is_configured:
            raise RuntimeError("Azure OpenAI is not configured.")

        filename = Path(uploaded_file.name).name
        text = self._extract_text(filename, uploaded_file.getvalue())
        chunks = self._chunk(text)

        if not chunks:
            return 0

        # Replace the previous version of the same file.
        existing = self.collection.get(where={"source": filename})
        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])

        embeddings = self._embed(chunks)
        ids = [f"{filename}:{i}" for i in range(len(chunks))]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=[
                {"source": filename, "chunk": i}
                for i in range(len(chunks))
            ],
        )
        return len(chunks)

    def retrieve(self, query: str) -> List[Dict]:
        query_embedding = self._embed([query])[0]
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=self.top_k,
        )

        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        sources = []
        for doc, meta, distance in zip(docs, metas, distances):
            sources.append({
                "text": doc,
                "file": meta.get("source", "unknown"),
                "chunk": meta.get("chunk", "?"),
                "distance": distance,
            })
        return sources

    def answer(self, question: str, history: List[Dict]) -> Dict:
        sources = self.retrieve(question)

        context = "\n\n".join(
            f"[Source {i+1} | {s['file']} | chunk {s['chunk']}]\n{s['text']}"
            for i, s in enumerate(sources)
        )

        system_prompt = """You are a helpful RAG assistant.

Answer the user's question using the supplied document context.
Rules:
1. Prefer the document context over general knowledge.
2. If the answer is not supported by the context, clearly say that the documents do not contain enough information.
3. Do not invent facts, citations, numbers, or document content.
4. Give concise, useful answers.
5. When useful, mention the source filename and chunk naturally.
"""

        messages = [{"role": "system", "content": system_prompt}]

        # Keep only recent conversational turns.
        for msg in history[-8:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        messages.append({
            "role": "user",
            "content": f"""Document context:

{context if context else "(No relevant documents found.)"}

Question:
{question}""",
        })

        # First API call with reasoning
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.open_router_chat_completion_api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "minimax/minimax-m3:free",
                "messages": messages,
                "reasoning": {"enabled": False}
            })
        )

        # Extract the assistant message with reasoning_details
        response = response.json()
        response = response['choices'][0]['message']

        return {
            "answer": response.get('content'),
            "sources": sources,
        }
