import os
import json
import pickle
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import re

@dataclass
class Entity:
    name: str
    entity_type: str
    chunk_ids: List[str]

@dataclass
class Relationship:
    subject: str
    relation: str
    object: str
    chunk_ids: List[str]
    confidence: float

@dataclass
class GraphSearchResult:
    entities: List[Entity]
    relationships: List[Relationship]
    related_chunk_ids: Set[str]
    relevance_score: float

class KnowledgeGraph:
    """
    Knowledge graph for entity and relationship extraction.
    Enables relationship-based retrieval and entity linking.
    """
    
    def __init__(self, graph_path: str = "./data/knowledge_graph"):
        self.graph_path = graph_path
        os.makedirs(graph_path, exist_ok=True)
        self.entities = {}
        self.relationships = {}
        self.chunk_to_entities = {}
        self.load_from_disk()
    
    def clear_graph(self):
        """Clear all graph data."""
        self.entities.clear()
        self.relationships.clear()
        self.chunk_to_entities.clear()
    
    def add_entity(
        self,
        entity_name: str,
        entity_type: str,
        chunk_id: str
    ) -> bool:
        """Add an entity to the knowledge graph."""
        entity_key = f"{entity_name}_{entity_type}".lower()
        
        if entity_key not in self.entities:
            self.entities[entity_key] = Entity(
                name=entity_name,
                entity_type=entity_type,
                chunk_ids=[chunk_id]
            )
        else:
            if chunk_id not in self.entities[entity_key].chunk_ids:
                self.entities[entity_key].chunk_ids.append(chunk_id)
        
        if chunk_id not in self.chunk_to_entities:
            self.chunk_to_entities[chunk_id] = []
        
        if entity_key not in self.chunk_to_entities[chunk_id]:
            self.chunk_to_entities[chunk_id].append(entity_key)
        
        return True
    
    def add_relationship(
        self,
        subject: str,
        relation: str,
        obj: str,
        chunk_id: str,
        confidence: float = 0.8
    ) -> bool:
        """Add a relationship (triplet) to the knowledge graph."""
        rel_key = f"{subject}_{relation}_{obj}".lower()
        
        if rel_key not in self.relationships:
            self.relationships[rel_key] = Relationship(
                subject=subject,
                relation=relation,
                object=obj,
                chunk_ids=[chunk_id],
                confidence=confidence
            )
        else:
            if chunk_id not in self.relationships[rel_key].chunk_ids:
                self.relationships[rel_key].chunk_ids.append(chunk_id)
        
        return True
    
    def extract_entities_from_metadata(self, metadata: Dict, chunk_id: str) -> List[Entity]:
        """
        Extract entities from structured SharePoint metadata (KPMG structure).
        No NER needed - entities come from metadata fields!
        """
        extracted = []
        
        # Client entity
        if metadata.get('client'):
            self.add_entity(metadata['client'], "CLIENT", chunk_id)
            extracted.append(Entity(metadata['client'], "CLIENT", [chunk_id]))
        
        # Service line entity
        if metadata.get('service_line'):
            self.add_entity(metadata['service_line'], "SERVICE_LINE", chunk_id)
            extracted.append(Entity(metadata['service_line'], "SERVICE_LINE", [chunk_id]))
        
        # Sector entity
        if metadata.get('sector'):
            self.add_entity(metadata['sector'], "SECTOR", chunk_id)
            extracted.append(Entity(metadata['sector'], "SECTOR", [chunk_id]))
        
        # Document type entity
        if metadata.get('document_type'):
            self.add_entity(metadata['document_type'], "DOCUMENT_TYPE", chunk_id)
            extracted.append(Entity(metadata['document_type'], "DOCUMENT_TYPE", [chunk_id]))
        
        # Engagement partner entity
        if metadata.get('engagement_partner'):
            self.add_entity(metadata['engagement_partner'], "PARTNER", chunk_id)
            extracted.append(Entity(metadata['engagement_partner'], "PARTNER", [chunk_id]))
        
        # CRM ID entity
        if metadata.get('crm_id'):
            self.add_entity(metadata['crm_id'], "CRM_OPPORTUNITY", chunk_id)
            extracted.append(Entity(metadata['crm_id'], "CRM_OPPORTUNITY", [chunk_id]))
        
        # Project ID entity
        if metadata.get('project_id'):
            self.add_entity(metadata['project_id'], "PROJECT", chunk_id)
            extracted.append(Entity(metadata['project_id'], "PROJECT", [chunk_id]))
        
        return extracted
    
    def extract_entities_from_text(self, text: str, chunk_id: str) -> List[Entity]:
        """
        Fallback: Extract entities from text using simple patterns.
        Used only if metadata is not available.
        """
        extracted = []
        
        # KPMG Service Lines
        service_pattern = r'\b(?:Business Consulting|Deal Advisory|Audit|Tax|Risk Advisory|ESG|Government & Enablement)\b'
        for match in re.finditer(service_pattern, text, re.IGNORECASE):
            entity_name = match.group()
            self.add_entity(entity_name, "SERVICE_LINE", chunk_id)
            extracted.append(Entity(entity_name, "SERVICE_LINE", [chunk_id]))
        
        # KPMG Sectors
        sector_pattern = r'\b(?:ENR|Government|Real Estate|FS|Retail|Insurance)\b'
        for match in re.finditer(sector_pattern, text):
            entity_name = match.group()
            self.add_entity(entity_name, "SECTOR", chunk_id)
            extracted.append(Entity(entity_name, "SECTOR", [chunk_id]))
        
        # Document types
        doc_type_pattern = r'\b(?:Proposal|Report|Notes|Email|Document|Presentation)\b'
        for match in re.finditer(doc_type_pattern, text):
            entity_name = match.group()
            self.add_entity(entity_name, "DOCUMENT_TYPE", chunk_id)
            extracted.append(Entity(entity_name, "DOCUMENT_TYPE", [chunk_id]))
        
        return extracted
    
    def extract_relationships_from_metadata(self, metadata: Dict, chunk_id: str) -> List[Relationship]:
        """
        Extract relationships from structured metadata (KPMG structure).
        Creates hierarchical relationships: Client → Sector → Service → Project → CRM
        """
        extracted = []
        
        client = metadata.get('client')
        service_line = metadata.get('service_line')
        sector = metadata.get('sector')
        doc_type = metadata.get('document_type')
        partner = metadata.get('engagement_partner')
        crm_id = metadata.get('crm_id')
        project_id = metadata.get('project_id')
        
        # Client → Sector relationship
        if client and sector:
            self.add_relationship(client, "IN_SECTOR", sector, chunk_id, 1.0)
            extracted.append(Relationship(client, "IN_SECTOR", sector, [chunk_id], 1.0))
        
        # Client → Service Line relationship
        if client and service_line:
            self.add_relationship(client, "HAS_SERVICE", service_line, chunk_id, 1.0)
            extracted.append(Relationship(client, "HAS_SERVICE", service_line, [chunk_id], 1.0))
        
        # Sector → Service Line relationship
        if sector and service_line:
            self.add_relationship(sector, "USES_SERVICE", service_line, chunk_id, 1.0)
            extracted.append(Relationship(sector, "USES_SERVICE", service_line, [chunk_id], 1.0))
        
        # Service Line → Document Type relationship
        if service_line and doc_type:
            self.add_relationship(service_line, "HAS_DOCUMENT", doc_type, chunk_id, 1.0)
            extracted.append(Relationship(service_line, "HAS_DOCUMENT", doc_type, [chunk_id], 1.0))
        
        # Partner → Project relationship
        if partner and project_id:
            self.add_relationship(partner, "MANAGES_PROJECT", project_id, chunk_id, 1.0)
            extracted.append(Relationship(partner, "MANAGES_PROJECT", project_id, [chunk_id], 1.0))
        
        # Project → CRM relationship
        if project_id and crm_id:
            self.add_relationship(project_id, "LINKED_TO_CRM", crm_id, chunk_id, 1.0)
            extracted.append(Relationship(project_id, "LINKED_TO_CRM", crm_id, [chunk_id], 1.0))
        
        # CRM → Client relationship
        if crm_id and client:
            self.add_relationship(crm_id, "FOR_CLIENT", client, chunk_id, 1.0)
            extracted.append(Relationship(crm_id, "FOR_CLIENT", client, [chunk_id], 1.0))
        
        # Client → Document Type relationship
        if client and doc_type:
            self.add_relationship(client, "HAS_DOCUMENT_TYPE", doc_type, chunk_id, 1.0)
            extracted.append(Relationship(client, "HAS_DOCUMENT_TYPE", doc_type, [chunk_id], 1.0))
        
        return extracted
    
    def extract_relationships_from_text(self, text: str, chunk_id: str) -> List[Relationship]:
        """
        Extract relationships from text using simple patterns.
        In production, would use dependency parsing.
        """
        extracted = []
        
        # Extract entities first to create relationships between them
        entities = self.extract_entities_from_text(text, chunk_id)
        
        # Create relationships between co-occurring entities
        if len(entities) >= 2:
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    # Different entity types = potential relationship
                    if entity1.entity_type != entity2.entity_type:
                        relation_type = f"{entity1.entity_type}_HAS_{entity2.entity_type}"
                        self.add_relationship(entity1.name, relation_type, entity2.name, chunk_id, 0.6)
                        extracted.append(Relationship(entity1.name, relation_type, entity2.name, [chunk_id], 0.6))
        
        # Pattern-based relationships
        patterns = [
            (r'(\w+)\s+(?:works|works for|employed by)\s+(\w+)', "WORKS_FOR"),
            (r'(\w+)\s+(?:manages|oversees|leads)\s+(\w+)', "MANAGES"),
            (r'(\w+)\s+(?:related to|associated with|connected to)\s+(\w+)', "RELATED_TO"),
        ]
        
        for pattern, relation_type in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                subject = match.group(1)
                obj = match.group(2)
                self.add_relationship(subject, relation_type, obj, chunk_id, 0.7)
                extracted.append(Relationship(subject, relation_type, obj, [chunk_id], 0.7))
        
        return extracted
    
    def query_entity(self, entity_name: str) -> Optional[Entity]:
        """Query an entity from the graph."""
        for entity_key, entity in self.entities.items():
            if entity.name.lower() == entity_name.lower():
                return entity
        return None
    
    def query_relationships(self, entity_name: str) -> List[Relationship]:
        """Get all relationships involving an entity."""
        related = []
        for rel in self.relationships.values():
            if rel.subject.lower() == entity_name.lower() or rel.object.lower() == entity_name.lower():
                related.append(rel)
        return related
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete all entities and relationships associated with a chunk."""
        if chunk_id not in self.chunk_to_entities:
            return True
        
        entity_keys = self.chunk_to_entities[chunk_id]
        
        for entity_key in entity_keys:
            if entity_key in self.entities:
                entity = self.entities[entity_key]
                if chunk_id in entity.chunk_ids:
                    entity.chunk_ids.remove(chunk_id)
                if not entity.chunk_ids:
                    del self.entities[entity_key]
        
        rel_keys_to_delete = []
        for rel_key, rel in self.relationships.items():
            if chunk_id in rel.chunk_ids:
                rel.chunk_ids.remove(chunk_id)
            if not rel.chunk_ids:
                rel_keys_to_delete.append(rel_key)
        
        for rel_key in rel_keys_to_delete:
            del self.relationships[rel_key]
        
        del self.chunk_to_entities[chunk_id]
        return True
    
    def search_by_entity(self, entity_name: str) -> GraphSearchResult:
        """Search graph for entity and related chunks."""
        entity = self.query_entity(entity_name)
        relationships = self.query_relationships(entity_name)
        
        related_chunk_ids = set()
        if entity:
            related_chunk_ids.update(entity.chunk_ids)
        
        for rel in relationships:
            related_chunk_ids.update(rel.chunk_ids)
        
        relevance_score = 0.5 + (len(relationships) * 0.1)
        relevance_score = min(relevance_score, 1.0)
        
        return GraphSearchResult(
            entities=[entity] if entity else [],
            relationships=relationships,
            related_chunk_ids=related_chunk_ids,
            relevance_score=relevance_score
        )
    
    def get_stats(self) -> Dict:
        """Get knowledge graph statistics."""
        return {
            "total_entities": len(self.entities),
            "total_relationships": len(self.relationships),
            "total_chunks_indexed": len(self.chunk_to_entities),
            "graph_path": self.graph_path
        }
    
    def load_from_disk(self):
        """Load graph from disk."""
        graph_file = f"{self.graph_path}/graph.pkl"
        if os.path.exists(graph_file):
            try:
                with open(graph_file, 'rb') as f:
                    data = pickle.load(f)
                    self.entities = data.get('entities', {})
                    self.relationships = data.get('relationships', {})
                    self.chunk_to_entities = data.get('chunk_to_entities', {})
            except:
                self.entities = {}
                self.relationships = {}
                self.chunk_to_entities = {}
    
    def save_to_disk(self):
        """Save graph to disk."""
        os.makedirs(self.graph_path, exist_ok=True)
        with open(f"{self.graph_path}/graph.pkl", 'wb') as f:
            pickle.dump({
                'entities': self.entities,
                'relationships': self.relationships,
                'chunk_to_entities': self.chunk_to_entities
            }, f)
