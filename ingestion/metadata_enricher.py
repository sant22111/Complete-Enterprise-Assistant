"""
Metadata Enricher - Combines SharePoint metadata with CRM data.
Handles the realistic scenario where 99% of documents don't have CRM IDs.
"""

import re
from typing import Dict, Optional
from datetime import datetime

class MetadataEnricher:
    """
    Enriches SharePoint document metadata with CRM system data.
    
    Strategy:
    1. Parse document content for CRM/Project IDs (1% of documents)
    2. If no ID found, match by client name + service line (99% of documents)
    3. Use most recent active opportunity as best match
    """
    
    def __init__(self, crm_api):
        self.crm_api = crm_api
    
    def enrich(self, sharepoint_metadata: dict, document_text: str) -> dict:
        """
        Combine SharePoint metadata + CRM data + content parsing.
        
        Args:
            sharepoint_metadata: Metadata from SharePoint (client, service_line, etc.)
            document_text: Extracted text from document
        
        Returns:
            Enriched metadata with CRM data (if found)
        """
        enriched = sharepoint_metadata.copy()
        
        # Step 1: Parse content for explicit CRM/Project IDs (rare - 1% of docs)
        content_metadata = self._parse_content_for_ids(document_text)
        if content_metadata:
            enriched.update(content_metadata)
        
        # Step 2: If we found a CRM ID, lookup in CRM system
        if enriched.get('crm_id'):
            crm_data = self.crm_api.get_opportunity_by_id(enriched['crm_id'])
            if crm_data:
                enriched.update(self._extract_crm_fields(crm_data))
                enriched['crm_match_method'] = 'explicit_id'
                enriched['crm_match_confidence'] = 1.0
                return enriched
        
        # Step 3: If we found a Project ID, lookup in CRM
        if enriched.get('project_id'):
            crm_data = self.crm_api.search_by_project(enriched['project_id'])
            if crm_data:
                enriched.update(self._extract_crm_fields(crm_data))
                enriched['crm_match_method'] = 'project_id'
                enriched['crm_match_confidence'] = 0.95
                return enriched
        
        # Step 4: No explicit ID - match by client + service line (99% of docs)
        if enriched.get('client') and enriched.get('service_line'):
            crm_data = self._match_by_client_and_service(
                enriched['client'],
                enriched['service_line'],
                enriched.get('year')
            )
            if crm_data:
                enriched.update(self._extract_crm_fields(crm_data))
                enriched['crm_match_method'] = 'client_service_match'
                enriched['crm_match_confidence'] = 0.75
                return enriched
        
        # Step 5: Fallback - match by client only
        if enriched.get('client'):
            crm_data = self._match_by_client_only(enriched['client'])
            if crm_data:
                enriched.update(self._extract_crm_fields(crm_data))
                enriched['crm_match_method'] = 'client_only_match'
                enriched['crm_match_confidence'] = 0.5
                return enriched
        
        # No CRM match found
        enriched['crm_match_method'] = 'none'
        enriched['crm_match_confidence'] = 0.0
        return enriched
    
    def _parse_content_for_ids(self, text: str) -> Dict:
        """
        Extract CRM/Project IDs from document content.
        Only ~1% of documents will have these explicitly mentioned.
        """
        metadata = {}
        
        # Only check first 2000 chars (IDs are usually at the top)
        text_sample = text[:2000] if text else ""
        
        # Pattern for CRM ID: CRM_XX_2024_001, CRM-XX-2024-001, etc.
        crm_pattern = r'CRM[_\s-]?(?:ID)?[:\s]*([A-Z]{1,4}[_-]?\d{4}[_-]?\d{3})'
        match = re.search(crm_pattern, text_sample, re.IGNORECASE)
        if match:
            metadata['crm_id'] = match.group(1).replace('-', '_').upper()
        
        # Pattern for Project ID: PROJ_2024_BC_001, PROJ-2024-BC-001, etc.
        project_pattern = r'(?:Project|PROJ)[_\s-]?(?:ID|Code)?[:\s]*([A-Z0-9_-]+)'
        match = re.search(project_pattern, text_sample, re.IGNORECASE)
        if match:
            metadata['project_id'] = match.group(1).replace('-', '_').upper()
        
        # Pattern for Engagement Partner
        partner_pattern = r'(?:Engagement Partner|Partner|Lead)[:\s]+([A-Z][a-z]+\s[A-Z][a-z]+)'
        match = re.search(partner_pattern, text_sample)
        if match:
            metadata['engagement_partner'] = match.group(1).strip()
        
        return metadata
    
    def _match_by_client_and_service(self, client: str, service_line: str, year: Optional[int] = None) -> Optional[Dict]:
        """
        Match document to CRM opportunity by client + service line.
        This handles 99% of documents that don't have explicit CRM IDs.
        """
        # Search CRM for matching opportunities
        opportunities = self.crm_api.search_by_client_and_service(client, service_line)
        
        if not opportunities:
            return None
        
        # Filter by year if provided
        if year:
            year_filtered = [
                opp for opp in opportunities
                if str(year) in opp['start_date'] or str(year) in opp['end_date']
            ]
            if year_filtered:
                opportunities = year_filtered
        
        # Prefer active opportunities
        active_opps = [opp for opp in opportunities if opp['status'] == 'Active']
        if active_opps:
            # Return most recent active opportunity
            return max(active_opps, key=lambda x: x['start_date'])
        
        # If no active, return most recent
        return max(opportunities, key=lambda x: x['start_date'])
    
    def _match_by_client_only(self, client: str) -> Optional[Dict]:
        """
        Fallback: Match by client name only.
        Lower confidence match.
        """
        opportunities = self.crm_api.get_active_opportunities_by_client(client)
        
        if not opportunities:
            # Try all opportunities if no active ones
            opportunities = self.crm_api.search_by_client(client)
        
        if not opportunities:
            return None
        
        # Return most recent
        return max(opportunities, key=lambda x: x['start_date'])
    
    def _extract_crm_fields(self, crm_data: Dict) -> Dict:
        """Extract relevant fields from CRM data."""
        return {
            'crm_id': crm_data.get('crm_id'),
            'project_id': crm_data.get('project_id'),
            'engagement_partner': crm_data.get('engagement_partner'),
            'sector': crm_data.get('sector'),
            'opportunity_name': crm_data.get('opportunity_name'),
            'crm_status': crm_data.get('status'),
            'crm_value': crm_data.get('value'),
            'crm_start_date': crm_data.get('start_date'),
            'crm_end_date': crm_data.get('end_date')
        }
