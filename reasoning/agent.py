from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI
import json
import requests
from reasoning.evidence_builder import EvidencePack

class ToolType(Enum):
    """Available tools for the agent."""
    SEARCH_VECTOR = "search_vector"
    SEARCH_KEYWORD = "search_keyword"
    SEARCH_GRAPH = "search_graph"
    RETRIEVE_ENTITY = "retrieve_entity"
    COMPARE_CHUNKS = "compare_chunks"
    SEARCH_WEB = "search_web"
    SYNTHESIZE = "synthesize"

@dataclass
class AgentAction:
    """Represents an action the agent wants to take."""
    tool: ToolType
    input: str
    reasoning: str

@dataclass
class AgentObservation:
    """Result of an agent action."""
    tool: ToolType
    input: str
    result: str
    confidence: float

@dataclass
class AgentThought:
    """Agent's reasoning step."""
    thought: str
    action: Optional[AgentAction]
    observation: Optional[AgentObservation]

@dataclass
class AgentResponse:
    """Final response from the agent."""
    answer: str
    reasoning_steps: List[AgentThought]
    sources: List[Dict]
    confidence: float
    api_calls: int
    total_cost_estimate: float
    input_tokens: int
    output_tokens: int
    total_tokens: int

class Agent:
    """
    Agentic reasoning layer for complex multi-step queries.
    Uses ReAct (Reasoning + Acting) pattern.
    """
    
    def __init__(self, 
                 api_key: str,
                 hybrid_retriever,
                 vector_store,
                 knowledge_graph,
                 embedding_service,
                 max_iterations: int = 5,
                 input_cost_per_1m: float = 2.00,
                 output_cost_per_1m: float = 6.00):
        """
        Initialize agent.
        
        Args:
            api_key: Grok API key
            hybrid_retriever: HybridRetriever instance
            vector_store: VectorStore instance
            knowledge_graph: KnowledgeGraph instance
            embedding_service: EmbeddingService for query embeddings
            max_iterations: Max reasoning steps
            input_cost_per_1m: Input cost per 1M tokens (grok-4.20: $2.00)
            output_cost_per_1m: Output cost per 1M tokens (grok-4.20: $6.00)
        """
        self.api_key = api_key
        self.hybrid_retriever = hybrid_retriever
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        self.embedding_service = embedding_service
        self.max_iterations = max_iterations
        self.input_cost_per_1m = input_cost_per_1m
        self.output_cost_per_1m = output_cost_per_1m
        
        # Detect which API based on key
        if "sk-" in api_key:  # OpenAI keys start with "sk-"
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4o"  # Latest OpenAI model
        else:  # Grok key
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1"
            )
            self.model = "grok-4-latest"
        
        self.api_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
    
    def think_and_act(self, query: str) -> AgentResponse:
        """
        Execute ReAct loop: Think → Act → Observe → Repeat.
        """
        self.api_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        reasoning_steps = []
        context = ""
        
        for iteration in range(self.max_iterations):
            # THINK: Decide what to do next
            thought_text, action = self._think(
                query=query,
                context=context,
                iteration=iteration
            )
            
            thought = AgentThought(
                thought=thought_text,
                action=action,
                observation=None
            )
            
            # Check if agent decided to finish
            if action is None or action.tool == ToolType.SYNTHESIZE:
                # Generate final answer
                final_answer = self._synthesize(query, context)
                thought.observation = AgentObservation(
                    tool=ToolType.SYNTHESIZE,
                    input=query,
                    result=final_answer,
                    confidence=0.9
                )
                reasoning_steps.append(thought)
                break
            
            # ACT: Execute the action
            observation = self._act(action)
            thought.observation = observation
            reasoning_steps.append(thought)
            
            # Update context with observation
            context += f"\n[{action.tool.value}] {observation.result}"
        
        # If we exited loop without synthesizing, force synthesis now
        if reasoning_steps and reasoning_steps[-1].observation.tool != ToolType.SYNTHESIZE:
            final_answer = self._synthesize(query, context)
            # Add synthesis step
            synthesis_thought = AgentThought(
                thought="Synthesizing final answer from gathered information",
                action=None,
                observation=AgentObservation(
                    tool=ToolType.SYNTHESIZE,
                    input=query,
                    result=final_answer,
                    confidence=0.9
                )
            )
            reasoning_steps.append(synthesis_thought)
        
        # Extract sources and build response
        sources = self._extract_sources(context)
        confidence = self._calculate_confidence(reasoning_steps)
        cost = self._estimate_cost()
        
        final_answer = reasoning_steps[-1].observation.result if reasoning_steps else "No answer generated"
        
        return AgentResponse(
            answer=final_answer,
            reasoning_steps=reasoning_steps,
            sources=sources,
            confidence=confidence,
            api_calls=self.api_calls,
            total_cost_estimate=cost,
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            total_tokens=self.total_input_tokens + self.total_output_tokens
        )
    
    def _think(self, query: str, context: str, iteration: int) -> Tuple[str, Optional[AgentAction]]:
        """
        Use Grok to reason about what to do next.
        """
        self.api_calls += 1
        
        prompt = f"""You are a reasoning agent. Your task is to answer this query by breaking it down into steps.

Query: {query}

Current Context:
{context if context else "No context yet. Start by searching for relevant information."}

Iteration: {iteration + 1}/{self.max_iterations}

Available Tools:
1. search_vector: Search internal knowledge base by semantic similarity
2. search_keyword: Search internal knowledge base by keywords (BM25)
3. search_graph: Search knowledge graph for entities and relationships
4. search_web: Search the web for external information (ALWAYS use this if internal search returns insufficient results or if query asks about current events, websites, or external companies)
5. retrieve_entity: Get details about a specific entity
6. compare_chunks: Compare two pieces of information
7. synthesize: Generate final answer

IMPORTANT: If internal searches don't find enough information, you MUST use search_web before synthesizing.
If the query mentions reading a website or getting current information, use search_web immediately.

Respond in this format:
THOUGHT: [Your reasoning about what to do next]
ACTION: [Tool name]
INPUT: [What to search/retrieve]

If you have enough information to answer, use ACTION: synthesize"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a reasoning agent that breaks down complex queries into steps."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            stream=False
        )
        
        response_text = response.choices[0].message.content
        self.total_input_tokens += response.usage.prompt_tokens
        self.total_output_tokens += response.usage.completion_tokens
        
        # Parse response
        thought_text = ""
        action = None
        
        lines = response_text.split('\n')
        for line in lines:
            if line.startswith("THOUGHT:"):
                thought_text = line.replace("THOUGHT:", "").strip()
            elif line.startswith("ACTION:"):
                tool_name = line.replace("ACTION:", "").strip().lower()
                # Find matching tool
                for tool in ToolType:
                    if tool.value == tool_name:
                        # Extract INPUT
                        input_text = ""
                        for next_line in lines:
                            if next_line.startswith("INPUT:"):
                                input_text = next_line.replace("INPUT:", "").strip()
                        
                        action = AgentAction(
                            tool=tool,
                            input=input_text,
                            reasoning=thought_text
                        )
                        break
        
        return thought_text, action
    
    def _act(self, action: AgentAction) -> AgentObservation:
        """
        Execute the action and return observation.
        """
        result = ""
        confidence = 0.0
        
        if action.tool == ToolType.SEARCH_VECTOR:
            # Vector search
            query_embedding = self.embedding_service.embed_query(action.input)
            chunks, _ = self.hybrid_retriever.retrieve(
                query=action.input,
                query_embedding=query_embedding,
                top_k=3
            )
            result = self._format_chunks(chunks)
            confidence = chunks[0].final_score if chunks else 0.0
        
        elif action.tool == ToolType.SEARCH_KEYWORD:
            # Keyword search
            query_embedding = self.embedding_service.embed_query(action.input)
            chunks, _ = self.hybrid_retriever.retrieve(
                query=action.input,
                query_embedding=query_embedding,
                top_k=3
            )
            result = self._format_chunks(chunks)
            confidence = 0.8
        
        elif action.tool == ToolType.SEARCH_GRAPH:
            # Graph search for entities
            graph_result = self.knowledge_graph.search_by_entity(action.input)
            result = self._format_entities(graph_result.entities)
            confidence = graph_result.relevance_score
        
        elif action.tool == ToolType.RETRIEVE_ENTITY:
            # Get entity details
            entity_key = action.input.lower().replace(" ", "_")
            if entity_key in self.knowledge_graph.entities:
                entity = self.knowledge_graph.entities[entity_key]
                result = f"Entity: {entity.name} ({entity.entity_type})\nChunks: {len(entity.chunk_ids)}"
                confidence = 0.9
            else:
                result = f"Entity '{action.input}' not found"
                confidence = 0.0
        
        elif action.tool == ToolType.COMPARE_CHUNKS:
            # Compare two pieces of info
            result = f"Comparison of: {action.input}"
            confidence = 0.7
        
        elif action.tool == ToolType.SEARCH_WEB:
            # Web search using DuckDuckGo (no API key needed)
            try:
                result = self._search_web(action.input)
                confidence = 0.8
            except Exception as e:
                result = f"Web search failed: {str(e)}"
                confidence = 0.0
        
        else:
            result = "Unknown tool"
            confidence = 0.0
        
        return AgentObservation(
            tool=action.tool,
            input=action.input,
            result=result,
            confidence=confidence
        )
    
    def _synthesize(self, query: str, context: str) -> str:
        """
        Generate final answer using all gathered context.
        """
        self.api_calls += 1
        
        prompt = f"""Based on the following research, provide a comprehensive answer to the query.

Query: {query}

Research Context:
{context}

IMPORTANT: 
- DO NOT just repeat the search results
- SYNTHESIZE the information into a coherent, well-written answer
- Use markdown formatting (headings, bullets, bold)
- If you found web sources, cite them properly with URLs
- If information is insufficient, clearly state what's missing and suggest next steps
- Write like a professional consultant, not a search engine

Provide a clear, well-structured answer:"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a synthesis expert. Combine information into clear answers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
            stream=False
        )
        
        answer = response.choices[0].message.content
        self.total_input_tokens += response.usage.prompt_tokens
        self.total_output_tokens += response.usage.completion_tokens
        
        return answer
    
    def _search_web(self, query: str) -> str:
        """
        Search the web using DuckDuckGo HTML search, then scrape top results.
        Returns content with citations.
        """
        try:
            # Search DuckDuckGo HTML (no API key needed)
            search_url = "https://html.duckduckgo.com/html/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Get search results
            response = requests.post(search_url, data={'q': query}, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return f"Web search failed with status {response.status_code}"
            
            # Parse HTML to extract URLs (simple extraction)
            html = response.text
            urls = []
            
            # Extract result URLs (look for result links)
            import re
            url_pattern = r'uddg=([^"&]+)'
            matches = re.findall(url_pattern, html)
            
            for match in matches[:3]:  # Top 3 results
                try:
                    from urllib.parse import unquote
                    decoded_url = unquote(match)
                    if decoded_url.startswith('http'):
                        urls.append(decoded_url)
                except:
                    continue
            
            if not urls:
                return f"No web results found for '{query}'. Try refining the search."
            
            # Scrape content from top URLs
            results = []
            for idx, url in enumerate(urls[:2], 1):  # Scrape top 2
                try:
                    page_response = requests.get(url, headers=headers, timeout=5)
                    if page_response.status_code == 200:
                        # Extract text content (simple extraction)
                        text = page_response.text
                        # Remove HTML tags
                        text = re.sub(r'<[^>]+>', ' ', text)
                        # Clean up whitespace
                        text = ' '.join(text.split())
                        # Take first 500 chars
                        snippet = text[:500]
                        
                        results.append(f"[Web Source {idx}] {url}\n{snippet}...")
                except Exception as e:
                    results.append(f"[Web Source {idx}] {url}\n(Could not fetch content)")
            
            if results:
                return "\n\n".join(results)
            else:
                return f"Web search found URLs but could not fetch content for '{query}'"
                
        except Exception as e:
            return f"Web search error: {str(e)}"
    
    def _format_chunks(self, chunks: List) -> str:
        """Format chunks for agent context."""
        if not chunks:
            return "No chunks found"
        
        formatted = ""
        for idx, chunk in enumerate(chunks[:3], 1):
            # Handle both dict and HybridSearchResult dataclass
            text = chunk.text if hasattr(chunk, 'text') else chunk.get('text', '')
            formatted += f"\n[Result {idx}] {text[:200]}...\n"
        return formatted
    
    def _format_entities(self, entities: List) -> str:
        """Format entities for agent context."""
        if not entities:
            return "No entities found"
        
        formatted = ""
        for entity in entities[:5]:
            formatted += f"\n- {entity.name} ({entity.entity_type})"
        return formatted
    
    def _extract_sources(self, context: str) -> List[Dict]:
        """Extract sources from context."""
        sources = []
        # Parse context to find document references
        for chunk_id in self.vector_store.chunks_store.keys():
            if chunk_id in context:
                chunk = self.vector_store.chunks_store[chunk_id]
                sources.append({
                    "chunk_id": chunk_id,
                    "document_id": chunk.get("document_id"),
                    "text": chunk.get("text", "")[:100]
                })
        return sources
    
    def _calculate_confidence(self, reasoning_steps: List[AgentThought]) -> float:
        """Calculate overall confidence from reasoning steps."""
        if not reasoning_steps:
            return 0.0
        
        confidences = [
            step.observation.confidence 
            for step in reasoning_steps 
            if step.observation
        ]
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _estimate_cost(self) -> float:
        """Calculate actual API cost based on real Grok pricing."""
        input_cost = (self.total_input_tokens / 1_000_000) * self.input_cost_per_1m
        output_cost = (self.total_output_tokens / 1_000_000) * self.output_cost_per_1m
        return input_cost + output_cost
