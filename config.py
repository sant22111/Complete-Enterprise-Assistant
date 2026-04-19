import os
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class StorageConfig:
    chroma_db_path: str = "./data/chroma_db"
    whoosh_index_path: str = "./data/whoosh_index"
    audit_log_path: str = "./logs/audit_logs.jsonl"
    ingestion_registry_path: str = "./logs/ingestion_registry.jsonl"

@dataclass
class ProcessingConfig:
    chunk_size: int = 400
    chunk_overlap: int = 100
    min_chunk_size: int = 50
    max_chunks_per_document: int = 1000

@dataclass
class RetrievalConfig:
    vector_weight: float = 0.5
    keyword_weight: float = 0.3
    graph_weight: float = 0.2
    top_k: int = 5
    similarity_threshold: float = 0.3

@dataclass
class LLMConfig:
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.3
    max_tokens: int = 1000
    api_key: str = os.getenv("OPENAI_API_KEY", "")

@dataclass
class GuardrailsConfig:
    enable_pii_detection: bool = True
    enable_toxicity_check: bool = True
    enable_hallucination_check: bool = True
    confidence_threshold: float = 0.6
    max_pii_score: float = 0.3

CLIENTS = {
    "flipkart": {"name": "Flipkart", "industry": "Retail"},
    "hdfc": {"name": "HDFC Bank", "industry": "Banking"},
    "airtel": {"name": "Airtel", "industry": "Telecom"},
    "apollo": {"name": "Apollo Hospitals", "industry": "Healthcare"},
}

SERVICE_LINES = ["Strategy", "Operations", "Technology", "Finance", "HR"]

DOCUMENT_TYPES = ["Proposal", "Final Report", "Internal Notes", "Meeting Notes", "Email"]

SENSITIVITY_LEVELS = ["Public", "Internal", "Confidential", "Restricted"]

PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "currency": r"\b(?:₹|Rs\.?|USD|\$|EUR|€)\s*[\d,]+(?:\.\d{2})?\b",
}

storage_config = StorageConfig()
processing_config = ProcessingConfig()
retrieval_config = RetrievalConfig()
llm_config = LLMConfig()
guardrails_config = GuardrailsConfig()
