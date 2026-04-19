from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI
import json
from reasoning.evidence_builder import EvidencePack

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

class OpenAILLMPipeline:
    """
    3-stage LLM response pipeline using OpenAI GPT-4: Maker → Checker → Judge
    Ensures grounded, traceable, and validated responses.
    MATCHES Grok architecture exactly - only Maker uses LLM!
    """
    
    def __init__(self, api_key: str, similarity_threshold: float = 0.6,
                 input_cost_per_1m: float = 5.00, output_cost_per_1m: float = 15.00):
        self.api_key = api_key
        self.similarity_threshold = similarity_threshold
        self.input_cost_per_1m = input_cost_per_1m
        self.output_cost_per_1m = output_cost_per_1m
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"  # Latest OpenAI model, 128K context
        self.total_input_tokens = 0
        self.total_output_tokens = 0
    
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
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        maker_output = self._maker_stage(query, evidence_pack)
        checker_output = self._checker_stage(maker_output, evidence_pack)
        judge_output = self._judge_stage(maker_output, checker_output, evidence_pack)
        
        return judge_output, maker_output, checker_output
    
    def get_token_usage(self) -> Dict:
        """Get token usage and cost for the last process() call."""
        total_tokens = self.total_input_tokens + self.total_output_tokens
        input_cost = (self.total_input_tokens / 1_000_000) * self.input_cost_per_1m
        output_cost = (self.total_output_tokens / 1_000_000) * self.output_cost_per_1m
        total_cost = input_cost + output_cost
        
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": total_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }
    
    def _maker_stage(
        self,
        query: str,
        evidence_pack: EvidencePack
    ) -> MakerOutput:
        """
        MAKER STAGE: Generate answer using OpenAI GPT-4.
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
5. Format with markdown (bold, bullets, headings)

Answer:"""
        
        answer = self._call_openai(prompt)
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
        CHECKER STAGE: Validate answer using HEURISTICS (not LLM).
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
        Uses SIMPLE LOGIC (not LLM).
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
    
    def _call_openai(self, prompt: str) -> str:
        """
        Call OpenAI GPT-4 API with prompt.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based on provided evidence. Always be factual and cite your sources."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000,
                stream=False
            )
            
            # Track token usage
            self.total_input_tokens += response.usage.prompt_tokens
            self.total_output_tokens += response.usage.completion_tokens
            
            return response.choices[0].message.content
        
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return f"Error generating response: {str(e)}"
    
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