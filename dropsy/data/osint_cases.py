"""
Dropsy OSINT: Realistic Threat Investigation Cases.
Bundles authentic open-source intelligence artifacts, Certificate Transparency logs,
cryptocurrency transaction flows, and breach correlation traces.
"""

from dropsy.core.entity_graph import OsintKnowledgeGraph, OsintEntity, OsintLink


def build_darkphish_investigation_case() -> OsintKnowledgeGraph:
    """
    Case 1: Operation DarkPhish.
    De-anonymizing a credential harvesting phishing campaign targeting online banking.
    Seed: 'chase-secure-verification.xyz' -> Real Actor: 'Alexander Perry'.
    """
    g = OsintKnowledgeGraph()

    # Tier 0: Seed Phishing Artifact
    g.add_entity(OsintEntity(
        id="domain_phish_01",
        name="chase-secure-verification.xyz",
        entity_type="DOMAIN",
        tier=0,
        confidence=0.10,
        details={"registrar": "NameCheap", "status": "Active Phishing", "created": "2026-10-14"},
        x=80, y=180
    ))

    # Tier 1: Infrastructure Layer
    g.add_entity(OsintEntity(
        id="ip_bulletproof",
        name="185.220.101.5 (Bulletproof Host)",
        entity_type="IP_ADDRESS",
        tier=1,
        confidence=0.30,
        details={"asn": "AS49981 Stark Industries", "country": "NL", "ports": "80, 443, 2222"},
        x=280, y=100
    ))
    g.add_entity(OsintEntity(
        id="ssl_cert_sn",
        name="Let's Encrypt Cert (SN: 04fa8b)",
        entity_type="SSL_CERT",
        tier=1,
        confidence=0.45,
        details={"issuer": "R3", "valid_to": "2027-01-12", "alt_names": "chase-secure-verification.xyz, alex-devlabs.ru"},
        x=280, y=260
    ))

    # Tier 2: Digital Identity Layer
    g.add_entity(OsintEntity(
        id="domain_old_portfolio",
        name="alex-devlabs.ru (Old Portfolio)",
        entity_type="DOMAIN",
        tier=2,
        confidence=0.60,
        details={"first_seen": "2023-04-10", "ssl_san_overlap": "TRUE"},
        x=500, y=100
    ))
    g.add_entity(OsintEntity(
        id="email_registrant",
        name="alex_darknet99@proton.me",
        entity_type="EMAIL",
        tier=2,
        confidence=0.75,
        details={"domain_ref": "alex-devlabs.ru", "breach_count": "2 collections"},
        x=500, y=260
    ))

    # Tier 3: Physical & Persona Corroboration
    g.add_entity(OsintEntity(
        id="handle_github",
        name="github.com/aperry-sec",
        entity_type="HANDLE",
        tier=3,
        confidence=0.90,
        details={"public_repos": "8", "pgp_fingerprint": "7F82 C914 B301 4A19", "utc_offset": "+03:00"},
        x=720, y=140
    ))
    g.add_entity(OsintEntity(
        id="crypto_monero",
        name="XMR/BTC Escrow (bc1q9...fjh)",
        entity_type="CRYPTO_WALLET",
        tier=3,
        confidence=0.85,
        details={"balance": "3.84 BTC", "mixer_hops": "2", "exchange": "Garantex"},
        x=720, y=320
    ))

    # Tier 4: Deanonymized Threat Actor Persona
    g.add_entity(OsintEntity(
        id="actor_alex_perry",
        name="Alexander Perry (Threat Actor)",
        entity_type="PERSON",
        tier=4,
        confidence=0.99,
        is_target_actor=True,
        details={"location": "Tbilisi / Moscow", "role": "Phishing Kit Author & Operator", "pgp_match": "VERIFIED"},
        evidence_tags=["PGP_KEY_MATCH", "BREACH_PASSWORD_HASH", "TIMEZONE_UTC+3", "COMMIT_METADATA"],
        x=930, y=200
    ))

    # Connect OSINT Pivot Links
    g.add_link(OsintLink("domain_phish_01", "ip_bulletproof", "RESOLVES_TO", 3.0, "Passive DNS (A Record)"))
    g.add_link(OsintLink("domain_phish_01", "ssl_cert_sn", "SIGNED_BY", 2.0, "crt.sh Certificate Transparency"))
    g.add_link(OsintLink("ssl_cert_sn", "domain_old_portfolio", "SHARED_CERT_SAN", 2.5, "crt.sh Subject Alternative Name"))
    g.add_link(OsintLink("ip_bulletproof", "domain_old_portfolio", "HOSTED_ON_SAME_IP", 3.5, "Shodan IP History"))
    g.add_link(OsintLink("domain_old_portfolio", "email_registrant", "HISTORICAL_WHOIS", 2.0, "SecurityTrails Whois Archive"))
    g.add_link(OsintLink("email_registrant", "handle_github", "BREACH_DATABASE_LINK", 2.5, "HaveIBeenPwned & Git Commits"))
    g.add_link(OsintLink("email_registrant", "crypto_monero", "TELEGRAM_ESCROW_LINK", 3.0, "Darknet Forum Telemetry"))
    g.add_link(OsintLink("handle_github", "actor_alex_perry", "PGP_AND_IDENTITY_MATCH", 1.5, "GPG Public Key & Resume Cross-Reference"))
    g.add_link(OsintLink("crypto_monero", "actor_alex_perry", "KYC_EXCHANGE_RECORDS", 2.0, "Exchange Compliance Ledger"))

    return g


def build_case_graph(case_id: str = "darkphish") -> OsintKnowledgeGraph:
    """Builds knowledge graph for the specified OSINT case."""
    return build_darkphish_investigation_case()


AVAILABLE_CASES = {
    "darkphish": {
        "id": "darkphish",
        "title": "Operation DarkPhish: Banking Phishing Campaign",
        "seed_id": "domain_phish_01",
        "target_id": "actor_alex_perry",
        "description": "De-anonymizing a credential-harvesting phishing network from a spoofed Chase banking domain to the real threat actor."
    }
}
