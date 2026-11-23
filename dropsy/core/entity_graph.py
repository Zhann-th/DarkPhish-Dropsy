"""
Dropsy OSINT: Entity Resolution & Intelligence Knowledge Graph.
Models digital footprints, entities, and obfuscation links for threat investigations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import json


@dataclass
class OsintEntity:
    id: str
    name: str
    entity_type: str  # 'DOMAIN', 'IP_ADDRESS', 'EMAIL', 'HANDLE', 'CRYPTO_WALLET', 'SSL_CERT', 'PERSON'
    tier: int         # 0: Seed Artifact, 1: Network Infra, 2: Digital Identity, 3: Core Anchor, 4: Real Persona
    confidence: float # 0.0 to 1.0 (Attribution confidence)
    details: Dict[str, str] = field(default_factory=dict)
    x: int = 0
    y: int = 0
    is_target_actor: bool = False
    evidence_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "tier": self.tier,
            "confidence": round(self.confidence, 4),
            "details": self.details,
            "x": self.x,
            "y": self.y,
            "is_target_actor": self.is_target_actor,
            "evidence_tags": list(self.evidence_tags),
        }


@dataclass
class OsintLink:
    source: str
    target: str
    relationship: str  # 'RESOLVES_TO', 'REGISTERED_BY', 'USES_ALIAS', 'TRANSACTED_WITH', 'SIGNED_BY'
    obfuscation_cost: float  # Difficulty to pivot across (Cloudflare, WHOIS privacy, VPN)
    source_record: str  # e.g. 'crt.sh CT log', 'PassiveTotal DNS', 'HaveIBeenPwned', 'Blockchain Ledger'
    verified: bool = True

    @property
    def traversal_cost(self) -> float:
        return self.obfuscation_cost

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "relationship": self.relationship,
            "obfuscation_cost": round(self.obfuscation_cost, 2),
            "source_record": self.source_record,
            "verified": self.verified,
        }


class OsintKnowledgeGraph:
    """
    Knowledge graph containing investigated threat entities and verifiable pivot links.
    """

    def __init__(self):
        self.entities: Dict[str, OsintEntity] = {}
        self.links: List[OsintLink] = []
        self.adjacency: Dict[str, List[Tuple[str, float]]] = {}

    def add_entity(self, entity: OsintEntity):
        self.entities[entity.id] = entity
        if entity.id not in self.adjacency:
            self.adjacency[entity.id] = []

    def add_link(self, link: OsintLink):
        self.links.append(link)
        self.adjacency.setdefault(link.source, []).append((link.target, link.traversal_cost))
        self.adjacency.setdefault(link.target, []).append((link.source, link.traversal_cost))

    def get_neighbors(self, entity_id: str) -> List[Tuple[str, float]]:
        return self.adjacency.get(entity_id, [])

    def to_dict(self) -> dict:
        return {
            "entities": [e.to_dict() for e in self.entities.values()],
            "links": [l.to_dict() for l in self.links],
        }
