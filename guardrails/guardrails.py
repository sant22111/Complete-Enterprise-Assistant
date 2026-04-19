import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from config import guardrails_config

@dataclass
class GuardrailCheckResult:
    passed: bool
    flags: List[str]
    pii_score: float
    toxicity_score: float
    hallucination_risk: float

class Guardrails:
    """
    Pre and post-generation guardrails to prevent data leakage and ensure safety.
    """
    
    def __init__(self):
        self.restricted_keywords = [
            "password", "api_key", "secret", "token", "credit_card",
            "ssn", "social_security", "bank_account", "routing_number"
        ]
        
        self.pii_patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        }
        
        self.toxic_words = [
            "hate", "kill", "destroy", "attack", "violence", "abuse"
        ]
    
    def pre_generation_check(self, query: str) -> GuardrailCheckResult:
        """
        Pre-generation checks: block restricted queries.
        """
        flags = []
        
        query_lower = query.lower()
        
        for keyword in self.restricted_keywords:
            if keyword in query_lower:
                flags.append(f"Restricted keyword detected: {keyword}")
        
        pii_score = self._detect_pii_in_query(query)
        if pii_score > guardrails_config.max_pii_score:
            flags.append(f"PII detected in query (score: {pii_score:.2f})")
        
        passed = len(flags) == 0
        
        return GuardrailCheckResult(
            passed=passed,
            flags=flags,
            pii_score=pii_score,
            toxicity_score=0.0,
            hallucination_risk=0.0
        )
    
    def post_generation_check(self, answer: str) -> GuardrailCheckResult:
        """
        Post-generation checks: detect PII leakage, toxicity, hallucinations.
        """
        flags = []
        
        pii_score = self._detect_pii_in_text(answer)
        if pii_score > guardrails_config.max_pii_score:
            flags.append(f"PII detected in response (score: {pii_score:.2f})")
        
        toxicity_score = self._detect_toxicity(answer)
        if toxicity_score > 0.5:
            flags.append(f"Toxic content detected (score: {toxicity_score:.2f})")
        
        hallucination_risk = self._estimate_hallucination_risk(answer)
        if hallucination_risk > 0.7:
            flags.append(f"High hallucination risk (score: {hallucination_risk:.2f})")
        
        passed = len(flags) == 0
        
        return GuardrailCheckResult(
            passed=passed,
            flags=flags,
            pii_score=pii_score,
            toxicity_score=toxicity_score,
            hallucination_risk=hallucination_risk
        )
    
    def _detect_pii_in_query(self, query: str) -> float:
        """Detect PII in query."""
        pii_count = 0
        total_patterns = len(self.pii_patterns)
        
        for pattern in self.pii_patterns.values():
            if re.search(pattern, query):
                pii_count += 1
        
        return pii_count / total_patterns if total_patterns > 0 else 0.0
    
    def _detect_pii_in_text(self, text: str) -> float:
        """Detect PII in generated text."""
        pii_count = 0
        total_patterns = len(self.pii_patterns)
        
        for pattern in self.pii_patterns.values():
            matches = re.findall(pattern, text)
            if matches:
                pii_count += 1
        
        return pii_count / total_patterns if total_patterns > 0 else 0.0
    
    def _detect_toxicity(self, text: str) -> float:
        """Detect toxic content in text."""
        text_lower = text.lower()
        toxic_count = 0
        
        for word in self.toxic_words:
            if word in text_lower:
                toxic_count += 1
        
        return min(1.0, toxic_count / max(1, len(self.toxic_words)))
    
    def _estimate_hallucination_risk(self, answer: str) -> float:
        """
        Estimate hallucination risk based on linguistic markers.
        High risk indicators: vague claims, unsupported assertions.
        """
        risk_score = 0.0
        
        vague_markers = ["probably", "maybe", "might", "could", "seems", "appears"]
        vague_count = sum(1 for marker in vague_markers if marker in answer.lower())
        risk_score += vague_count * 0.1
        
        absolute_markers = ["definitely", "certainly", "always", "never"]
        absolute_count = sum(1 for marker in absolute_markers if marker in answer.lower())
        risk_score += absolute_count * 0.15
        
        if len(answer) < 50:
            risk_score += 0.2
        
        return min(1.0, risk_score)
    
    def sanitize_response(self, answer: str) -> str:
        """Sanitize response by redacting detected PII."""
        sanitized = answer
        
        for pii_type, pattern in self.pii_patterns.items():
            replacement = f"[REDACTED_{pii_type.upper()}]"
            sanitized = re.sub(pattern, replacement, sanitized)
        
        return sanitized
