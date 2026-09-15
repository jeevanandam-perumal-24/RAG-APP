import os
import streamlit as st
import re
from pathlib import Path
from typing import List, Dict

import chromadb
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
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))

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

    def _embed(self, texts: List[str] | str) -> List[List[float]]:
        embeddings = []
        for text in texts:
            result = self.gemini_client.models.embed_content(
                        model="gemini-embedding-001",
                        contents=text
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
        context: str | None = None
        if st.session_state.authenticated:
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
                6. If the user's query is greetings, farwell or friendly talk means you can response in a friendly direct answer without using the document context.
                7. Respond like a human, not like an AI model. Avoid phrases like "As an AI language model" or "As an AI assistant".
                8. Generate a response in JSON format with the following keys:
                    - "answer": The answer to the user's question.
                    - "isSourceUsed": true if the answer is based on the document context, false otherwise.
                Note: Response must be valid JSON. Do not include any text outside the JSON object.

                Sample response:
                1. If the answer is based on the document context:
                {
                    "answer": "The document context provides information about the topic.",
                    "isSourceUsed": true
                }
                2. If the answer is not based on the document context:
                {
                    "answer": "I don't have information about that in the documents.",
                    "isSourceUsed": false
                }
                3. If the user's query is greetings, farwell or friendly talk:
                {
                    "answer": "Respective greeting/farwell response",
                    "isSourceUsed": false
                }
                """
        else:
            system_prompt = """
                You are a helpful RAG assistant. Answer the user's question using the supplied document context.
                Rules:
                    1. Give brief, formatted and useful answers.
                    2. Respond like a human, not like an AI model. Avoid phrases like "As an AI language model" or "As an AI assistant".
                    3. While answering user's query other than greeting / farwell, generate response with atleast 100 words.
                    4. Generate a response in JSON format with the following keys:
                        - "answer": The answer to the user's question.
                        - "isSourceUsed": true if the answer is based on the document context in , false otherwise.
                Note: Response must be valid JSON. Do not include any text outside the JSON object.
                Sample Response:
                    {
                        "answer": <GENERATED_RESPONSE>,
                        "isSourceUsed": true / false
                    }
            """
        messages = [{"role": "system", "content": system_prompt}]

        # Keep only recent conversational turns.
        for msg in history[-8:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        if context is None:
            messages.append({
                "role": "user",
                "content": f"""Question:{question}"""
            })
        else:
            messages.append({
                "role": "user",
                "content": f"""Document context:
{context if context else "(No relevant documents found.)"}
Question:
{question}""",})

        final_message = ""
        for message in messages:
            final_message += f"{message.get('role').__str__()}: {message.get('content').__str__()}"

        # First API call with reasoning
        response = self.gemini_client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=final_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json"
            )
        )

        # Extract the assistant message with reasoning_details
        final_response = json.loads(response.text)

        if final_response.get("isSourceUsed") is False:
            return {
                    "answer": final_response.get("answer"),
                    "sources": [],
                }
        else:
            return {
                    "answer": final_response.get("answer"),
                    "sources": sources,
                }
