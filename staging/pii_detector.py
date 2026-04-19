import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from config import PII_PATTERNS

@dataclass
class PIIMatch:
    pii_type: str
    original_text: str
    start_pos: int
    end_pos: int
    confidence: float = 0.95

class PIIDetector:
    """
    Detects Personally Identifiable Information (PII) in text.
    Supports: emails, phone numbers, SSN, credit cards, currency amounts.
    """
    
    def __init__(self):
        self.patterns = PII_PATTERNS
        self.pii_replacements = {
            "email": "[REDACTED_EMAIL]",
            "phone": "[REDACTED_PHONE]",
            "ssn": "[REDACTED_SSN]",
            "credit_card": "[REDACTED_CREDIT_CARD]",
            "currency": "[REDACTED_AMOUNT]",
        }
    
    def detect_pii(self, text: str) -> List[PIIMatch]:
        """Detect all PII in text and return matches."""
        matches = []
        
        for pii_type, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                pii_match = PIIMatch(
                    pii_type=pii_type,
                    original_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.95
                )
                matches.append(pii_match)
        
        return sorted(matches, key=lambda x: x.start_pos)
    
    def redact_pii(self, text: str, pii_matches: List[PIIMatch]) -> Tuple[str, List[Dict]]:
        """
        Redact PII in text and return redacted text + redaction log.
        """
        redaction_log = []
        offset = 0
        redacted_text = text
        
        for match in pii_matches:
            replacement = self.pii_replacements.get(match.pii_type, "[REDACTED]")
            
            start = match.start_pos + offset
            end = match.end_pos + offset
            
            redaction_log.append({
                "pii_type": match.pii_type,
                "original_text": match.original_text,
                "replacement": replacement,
                "position": match.start_pos,
                "confidence": match.confidence
            })
            
            redacted_text = redacted_text[:start] + replacement + redacted_text[end:]
            offset += len(replacement) - (match.end_pos - match.start_pos)
        
        return redacted_text, redaction_log
    
    def detect_and_redact(self, text: str) -> Tuple[str, List[Dict], List[PIIMatch]]:
        """Detect PII and return redacted text with logs."""
        matches = self.detect_pii(text)
        redacted_text, redaction_log = self.redact_pii(text, matches)
        return redacted_text, redaction_log, matches
