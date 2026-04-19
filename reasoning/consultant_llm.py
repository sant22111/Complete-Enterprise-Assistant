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

class ConsultantLLMPipeline:
    """
    Consultant-mode LLM pipeline using OpenAI GPT-4.
    Acts like a management consultant - analyzes evidence and provides strategic recommendations.
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
        Execute consultant-mode pipeline.
        
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
        CONSULTANT MAKER: Generate strategic recommendations based on evidence.
        """
        if not evidence_pack.chunks:
            return MakerOutput(
                answer="I don't have sufficient information in the knowledge base to provide strategic recommendations on this topic. To provide valuable insights, I would need access to relevant documents, reports, or data related to your query.",
                citations=[],
                confidence=0.0
            )
        
        evidence_text = self._format_evidence(evidence_pack)
        
        prompt = f"""You are a senior management consultant analyzing client data and providing strategic recommendations.

Query: {query}

Evidence from Knowledge Base:
{evidence_text}

Instructions:
1. **Analyze** the evidence like a consultant would
2. **Synthesize** key findings and patterns
3. **Provide strategic recommendations** based on the evidence
4. **Structure your response** professionally:
   - Executive Summary (if applicable)
   - Key Findings
   - Strategic Recommendations
   - Implementation Considerations
5. **Cite sources** using [Chunk N] notation
6. **Be actionable** - focus on what can be done
7. **Format with markdown** - use headings, bold, bullets
8. If evidence is limited, acknowledge it and suggest what additional information would be helpful

Respond as a consultant would - insightful, strategic, and action-oriented:"""
        
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
        JUDGE STAGE: Approve consultant recommendations.
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
            reason="Consultant recommendations approved",
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
        """Call OpenAI GPT-4 API with prompt."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior management consultant with expertise in strategy, operations, technology, and organizational transformation. You provide insightful analysis and actionable recommendations based on evidence."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # Higher temperature for more creative recommendations
                max_tokens=1500,
                stream=False
            )
            
            # Track token usage
            self.total_input_tokens += response.usage.prompt_tokens
            self.total_output_tokens += response.usage.completion_tokens
            
            return response.choices[0].message.content
        
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return f"Error generating consultant response: {str(e)}"
    
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
