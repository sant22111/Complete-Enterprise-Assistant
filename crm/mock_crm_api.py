"""
Mock CRM API - Simulates Salesforce/Dynamics CRM system.
Contains structured opportunity, project, and client data.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class CRMOpportunity:
    """CRM Opportunity record."""
    def __init__(self, crm_id: str, client: str, sector: str, service_line: str,
                 opportunity_name: str, project_id: str, engagement_partner: str,
                 status: str, value: int, start_date: str, end_date: str):
        self.crm_id = crm_id
        self.client = client
        self.sector = sector
        self.service_line = service_line
        self.opportunity_name = opportunity_name
        self.project_id = project_id
        self.engagement_partner = engagement_partner
        self.status = status
        self.value = value
        self.start_date = start_date
        self.end_date = end_date
    
    def to_dict(self):
        return {
            'crm_id': self.crm_id,
            'client': self.client,
            'sector': self.sector,
            'service_line': self.service_line,
            'opportunity_name': self.opportunity_name,
            'project_id': self.project_id,
            'engagement_partner': self.engagement_partner,
            'status': self.status,
            'value': self.value,
            'start_date': self.start_date,
            'end_date': self.end_date
        }

class MockCRMAPI:
    """
    Mock CRM system with KPMG opportunity data.
    Simulates Salesforce/Dynamics CRM.
    """
    
    def __init__(self):
        self.opportunities = self._generate_crm_opportunities()
    
    def _generate_crm_opportunities(self) -> Dict[str, CRMOpportunity]:
        """Generate realistic KPMG CRM opportunities."""
        
        # KPMG structure
        clients = [
            ("Flipkart", "Retail"),
            ("HDFC Bank", "FS"),
            ("Airtel", "ENR"),
            ("Apollo Hospitals", "Government"),
            ("Tata Steel", "ENR"),
            ("ICICI Bank", "FS"),
            ("Reliance Retail", "Retail"),
            ("Max Life Insurance", "Insurance"),
            ("DLF", "Real Estate"),
            ("Infosys", "Government")
        ]
        
        service_lines = [
            "Business Consulting",
            "Deal Advisory",
            "Audit",
            "Tax",
            "Risk Advisory",
            "ESG",
            "Government & Enablement"
        ]
        
        partners = [
            "John Smith",
            "Sarah Johnson",
            "Mike Chen",
            "Priya Sharma",
            "Rajesh Kumar",
            "Emily Davis",
            "David Lee",
            "Anita Patel"
        ]
        
        opportunities = {}
        opp_id = 1
        
        # Generate 2-3 opportunities per client
        for client, sector in clients:
            num_opps = random.randint(2, 3)
            
            for i in range(num_opps):
                service = random.choice(service_lines)
                partner = random.choice(partners)
                
                # Generate dates
                start_date = datetime.now() - timedelta(days=random.randint(30, 365))
                end_date = start_date + timedelta(days=random.randint(90, 365))
                
                # CRM ID format: CRM_{CLIENT_CODE}_{YEAR}_{NUMBER}
                client_code = ''.join([c[0] for c in client.split()[:2]]).upper()
                year = start_date.year
                crm_id = f"CRM_{client_code}_{year}_{opp_id:03d}"
                
                # Project ID format: PROJ_{YEAR}_{SERVICE_CODE}_{NUMBER}
                service_code = ''.join([c[0] for c in service.split()[:2]]).upper()
                project_id = f"PROJ_{year}_{service_code}_{opp_id:03d}"
                
                # Opportunity name
                initiatives = [
                    "Digital Transformation",
                    "Cloud Migration",
                    "Process Optimization",
                    "Risk Assessment",
                    "Compliance Review",
                    "M&A Advisory",
                    "Tax Planning",
                    "ESG Strategy",
                    "Cybersecurity Enhancement"
                ]
                opp_name = f"{client} - {random.choice(initiatives)}"
                
                # Status
                status = random.choice(["Active", "Active", "Active", "Closed Won", "Closed Lost"])
                
                # Value (in USD)
                value = random.randint(500000, 10000000)
                
                opp = CRMOpportunity(
                    crm_id=crm_id,
                    client=client,
                    sector=sector,
                    service_line=service,
                    opportunity_name=opp_name,
                    project_id=project_id,
                    engagement_partner=partner,
                    status=status,
                    value=value,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d")
                )
                
                opportunities[crm_id] = opp
                opp_id += 1
        
        return opportunities
    
    def get_opportunity_by_id(self, crm_id: str) -> Optional[Dict]:
        """Get CRM opportunity by ID."""
        opp = self.opportunities.get(crm_id)
        return opp.to_dict() if opp else None
    
    def search_by_client(self, client_name: str) -> List[Dict]:
        """Find all opportunities for a client."""
        results = []
        for opp in self.opportunities.values():
            if opp.client.lower() == client_name.lower():
                results.append(opp.to_dict())
        return results
    
    def search_by_project(self, project_id: str) -> Optional[Dict]:
        """Find opportunity by project ID."""
        for opp in self.opportunities.values():
            if opp.project_id == project_id:
                return opp.to_dict()
        return None
    
    def search_by_client_and_service(self, client_name: str, service_line: str) -> List[Dict]:
        """
        Find opportunities matching client and service line.
        Used to link documents without explicit CRM ID.
        """
        results = []
        for opp in self.opportunities.values():
            if (opp.client.lower() == client_name.lower() and 
                opp.service_line.lower() == service_line.lower()):
                results.append(opp.to_dict())
        return results
    
    def get_active_opportunities_by_client(self, client_name: str) -> List[Dict]:
        """Get only active opportunities for a client."""
        results = []
        for opp in self.opportunities.values():
            if (opp.client.lower() == client_name.lower() and 
                opp.status == "Active"):
                results.append(opp.to_dict())
        return results
    
    def list_all_opportunities(self) -> List[Dict]:
        """List all CRM opportunities."""
        return [opp.to_dict() for opp in self.opportunities.values()]
    
    def get_stats(self) -> Dict:
        """Get CRM statistics."""
        total = len(self.opportunities)
        active = sum(1 for opp in self.opportunities.values() if opp.status == "Active")
        total_value = sum(opp.value for opp in self.opportunities.values())
        
        return {
            "total_opportunities": total,
            "active_opportunities": active,
            "total_value": total_value,
            "clients": len(set(opp.client for opp in self.opportunities.values())),
            "service_lines": len(set(opp.service_line for opp in self.opportunities.values()))
        }
