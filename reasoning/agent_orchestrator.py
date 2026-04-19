"""
Agent Orchestrator - Manages both RAG and Agentic modes.
Provides cost optimization and mode selection.
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from reasoning.grok_llm import GrokLLMPipeline
from reasoning.agent import Agent
from reasoning.evidence_builder import EvidencePack

class QueryMode(Enum):
    """Query processing mode."""
    RAG = "rag"  # Fast, cheap, for simple queries
    AGENTIC = "agentic"  # Powerful, for complex queries
    AUTO = "auto"  # Automatically choose based on query complexity

@dataclass
class OrchestratorResponse:
    """Response from orchestrator."""
    mode_used: str
    answer: str
    sources: list
    confidence: float
    api_calls: int
    cost_estimate: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_steps: Optional[list] = None
    validation: Optional[Dict] = None

class AgentOrchestrator:
    """
    Orchestrates between RAG and Agentic modes.
    Optimizes for cost and performance.
    """
    
    def __init__(self,
                 grok_pipeline: GrokLLMPipeline,
                 agent: Agent,
                 complexity_threshold: float = 0.6):
        """
        Initialize orchestrator.
        
        Args:
            grok_pipeline: GrokLLMPipeline for RAG mode
            agent: Agent for agentic mode
            complexity_threshold: Threshold for auto mode (0-1)
        """
        self.grok_pipeline = grok_pipeline
        self.agent = agent
        self.complexity_threshold = complexity_threshold
    
    def process_query(self,
                     query: str,
                     evidence_pack: EvidencePack,
                     mode: QueryMode = QueryMode.AUTO) -> OrchestratorResponse:
        """
        Process query in selected mode.
        
        Args:
            query: User query
            evidence_pack: Retrieved evidence
            mode: Processing mode (RAG, AGENTIC, or AUTO)
        
        Returns:
            OrchestratorResponse with answer and metadata
        """
        # Determine mode if AUTO
        if mode == QueryMode.AUTO:
            complexity = self._estimate_query_complexity(query, evidence_pack)
            mode = QueryMode.AGENTIC if complexity > self.complexity_threshold else QueryMode.RAG
        
        if mode == QueryMode.RAG:
            return self._process_rag(query, evidence_pack)
        else:
            return self._process_agentic(query, evidence_pack)
    
    def _process_rag(self, query: str, evidence_pack: EvidencePack) -> OrchestratorResponse:
        """
        Process query using RAG pipeline (fast, cheap).
        """
        judge_output, maker_output, checker_output = self.grok_pipeline.process(
            query=query,
            evidence_pack=evidence_pack
        )
        
        # Get actual token usage and cost
        token_usage = self.grok_pipeline.get_token_usage()
        
        return OrchestratorResponse(
            mode_used="RAG",
            answer=judge_output.final_answer or "No answer generated",
            sources=maker_output.citations,
            confidence=judge_output.confidence,
            api_calls=1,
            cost_estimate=token_usage["total_cost"],
            input_tokens=token_usage["input_tokens"],
            output_tokens=token_usage["output_tokens"],
            total_tokens=token_usage["total_tokens"],
            validation={
                "is_grounded": checker_output.is_grounded,
                "semantic_similarity": checker_output.semantic_similarity,
                "has_unsupported_claims": checker_output.has_unsupported_claims,
                "issues": checker_output.issues
            }
        )
    
    def _process_agentic(self, query: str, evidence_pack: EvidencePack) -> OrchestratorResponse:
        """
        Process query using agentic reasoning (powerful, more expensive).
        """
        agent_response = self.agent.think_and_act(query)
        
        return OrchestratorResponse(
            mode_used="AGENTIC",
            answer=agent_response.answer,
            sources=agent_response.sources,
            confidence=agent_response.confidence,
            api_calls=agent_response.api_calls,
            cost_estimate=agent_response.total_cost_estimate,
            input_tokens=agent_response.input_tokens,
            output_tokens=agent_response.output_tokens,
            total_tokens=agent_response.total_tokens,
            reasoning_steps=[
                {
                    "thought": step.thought,
                    "action": step.action.tool.value if step.action else None,
                    "observation": step.observation.result if step.observation else None
                }
                for step in agent_response.reasoning_steps
            ]
        )
    
    def _estimate_query_complexity(self, query: str, evidence_pack: EvidencePack) -> float:
        """
        Estimate query complexity (0-1).
        Higher = more complex = use agentic mode.
        """
        complexity = 0.0
        
        # Factor 1: Query length (longer = more complex)
        query_words = len(query.split())
        complexity += min(query_words / 50, 0.3)  # Max 0.3
        
        # Factor 2: Multiple questions (use "and", "or", "compare")
        multi_question_keywords = ["and", "or", "compare", "vs", "versus", "difference"]
        if any(keyword in query.lower() for keyword in multi_question_keywords):
            complexity += 0.3
        
        # Factor 3: Evidence quality (low confidence = need more reasoning)
        if evidence_pack.chunks:
            avg_confidence = evidence_pack.total_confidence
            if avg_confidence < 0.6:
                complexity += 0.2
        else:
            complexity += 0.2  # No evidence = need reasoning
        
        # Factor 4: Reasoning keywords
        reasoning_keywords = ["why", "how", "explain", "analyze", "summarize", "relationship"]
        if any(keyword in query.lower() for keyword in reasoning_keywords):
            complexity += 0.2
        
        return min(complexity, 1.0)
    
    def get_cost_comparison(self, query: str, evidence_pack: EvidencePack) -> Dict:
        """
        Get cost comparison between RAG and agentic modes.
        """
        complexity = self._estimate_query_complexity(query, evidence_pack)
        
        rag_cost = 0.02  # 1 API call
        agentic_cost = 0.10  # ~5 API calls average
        
        return {
            "query_complexity": complexity,
            "rag_cost": rag_cost,
            "agentic_cost": agentic_cost,
            "cost_ratio": agentic_cost / rag_cost,
            "recommended_mode": "AGENTIC" if complexity > self.complexity_threshold else "RAG",
            "savings_with_rag": agentic_cost - rag_cost
        }
