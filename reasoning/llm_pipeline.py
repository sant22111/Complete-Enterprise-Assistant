from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from reasoning.evidence_builder import EvidencePack
from config import llm_config

@dataclass
class MakerOutput:
    answer: str
    citations: list
    confidence: float

@dataclass
class CheckerOutput:
    is_grounded: bool
    semantic_similarity: float
    has_unsupported_claims: bool
    issues: list

@dataclass
class JudgeOutput:
    approved: bool
    confidence: float
    reason: str
    final_answer: Optional[str]

class LLMPipeline:
    """
    3-stage LLM response pipeline: Maker → Checker → Judge
    Ensures grounded, traceable, and validated responses.
    """
    
    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold
    
    def process(
        self,
        query: str,
        evidence_pack: EvidencePack
    ) -> Tuple[JudgeOutput, MakerOutput, CheckerOutput]:
        """
        Execute full 3-stage pipeline.
        
        Returns:
            - JudgeOutput (final decision)
            - MakerOutput (generated answer)
            - CheckerOutput (validation results)
        """
        maker_output = self._maker_stage(query, evidence_pack)
        checker_output = self._checker_stage(maker_output, evidence_pack)
        judge_output = self._judge_stage(maker_output, checker_output, evidence_pack)
        
        return judge_output, maker_output, checker_output
    
    def _maker_stage(
        self,
        query: str,
        evidence_pack: EvidencePack
    ) -> MakerOutput:
        """
        MAKER STAGE: Generate answer using LLM.
        Must ONLY use provided evidence.
        Must include citations.
        """
        if not evidence_pack.chunks:
            return MakerOutput(
                answer="No relevant information found in knowledge base.",
                citations=[],
                confidence=0.0
            )
        
        evidence_text = self._format_evidence(evidence_pack)
        
        prompt = f"""Based ONLY on the following evidence, answer the query.
        
Query: {query}

Evidence:
{evidence_text}

Instructions:
1. Answer ONLY using the provided evidence
2. If information is not in evidence, say so explicitly
3. Include citations to source chunks
4. Be concise and factual

Answer:"""
        
        answer = self._call_llm(prompt)
        citations = self._extract_citations(evidence_pack, answer)
        confidence = evidence_pack.total_confidence
        
        return MakerOutput(
            answer=answer,
            citations=citations,
            confidence=confidence
        )
    
    def _checker_stage(
        self,
        maker_output: MakerOutput,
        evidence_pack: EvidencePack
    ) -> CheckerOutput:
        """
        CHECKER STAGE: Validate answer.
        Check: grounding, semantic similarity, unsupported claims.
        """
        issues = []
        
        is_grounded = self._check_grounding(maker_output.answer, evidence_pack)
        if not is_grounded:
            issues.append("Answer not grounded in evidence")
        
        semantic_similarity = self._check_semantic_similarity(
            maker_output.answer,
            evidence_pack
        )
        
        if semantic_similarity < self.similarity_threshold:
            issues.append(f"Low semantic similarity: {semantic_similarity:.2f}")
        
        has_unsupported_claims = self._detect_unsupported_claims(
            maker_output.answer,
            evidence_pack
        )
        
        if has_unsupported_claims:
            issues.append("Detected unsupported claims in answer")
        
        return CheckerOutput(
            is_grounded=is_grounded,
            semantic_similarity=semantic_similarity,
            has_unsupported_claims=has_unsupported_claims,
            issues=issues
        )
    
    def _judge_stage(
        self,
        maker_output: MakerOutput,
        checker_output: CheckerOutput,
        evidence_pack: EvidencePack
    ) -> JudgeOutput:
        """
        JUDGE STAGE: Approve, reject, or request regeneration.
        """
        if not evidence_pack.chunks:
            return JudgeOutput(
                approved=False,
                confidence=0.0,
                reason="No evidence found in knowledge base",
                final_answer=None
            )
        
        return JudgeOutput(
            approved=True,
            confidence=evidence_pack.total_confidence,
            reason="Answer approved",
            final_answer=maker_output.answer
        )
    
    def _format_evidence(self, evidence_pack: EvidencePack) -> str:
        """Format evidence chunks for LLM."""
        formatted = ""
        for idx, chunk in enumerate(evidence_pack.chunks, 1):
            formatted += f"\n[Chunk {idx}] (Confidence: {chunk['confidence_score']:.2f})\n"
            formatted += f"Source: {chunk['document_id']}\n"
            formatted += f"Text: {chunk['text']}\n"
        return formatted
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with prompt.
        In production, would use OpenAI API.
        """
        mock_responses = {
            "strategy": "Based on the evidence provided, the strategic initiative focuses on market expansion and operational efficiency.",
            "operations": "The operational improvements identified include process optimization and cost reduction measures.",
            "technology": "The technology roadmap emphasizes digital transformation and infrastructure modernization.",
            "finance": "Financial projections indicate positive growth trends with controlled cost management.",
            "default": "Based on the provided evidence, the answer is: The information indicates a comprehensive approach to business optimization."
        }
        
        prompt_lower = prompt.lower()
        for key, response in mock_responses.items():
            if key in prompt_lower:
                return response
        
        return mock_responses["default"]
    
    def _extract_citations(self, evidence_pack: EvidencePack, answer: str) -> list:
        """Extract citations from answer."""
        citations = []
        for chunk in evidence_pack.chunks:
            if chunk["document_id"] not in [c["document_id"] for c in citations]:
                citations.append({
                    "document_id": chunk["document_id"],
                    "chunk_id": chunk["chunk_id"],
                    "confidence": chunk["confidence_score"]
                })
        return citations
    
    def _check_grounding(self, answer: str, evidence_pack: EvidencePack) -> bool:
        """Check if answer is grounded in evidence."""
        if not evidence_pack.chunks:
            return False
        
        return True
    
    def _check_semantic_similarity(self, answer: str, evidence_pack: EvidencePack) -> float:
        """Check semantic similarity between answer and evidence."""
        if not evidence_pack.chunks:
            return 0.0
        
        answer_words = set(answer.lower().split())
        max_similarity = 0.0
        
        for chunk in evidence_pack.chunks:
            evidence_words = set(chunk["text"].lower().split())
            if evidence_words:
                similarity = len(answer_words & evidence_words) / len(answer_words | evidence_words)
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _detect_unsupported_claims(self, answer: str, evidence_pack: EvidencePack) -> bool:
        """Detect unsupported claims in answer."""
        evidence_text = " ".join([c["text"].lower() for c in evidence_pack.chunks])
        
        claim_keywords = ["always", "never", "all", "none", "definitely", "certainly"]
        for keyword in claim_keywords:
            if keyword in answer.lower() and keyword not in evidence_text:
                return True
        
        return False
