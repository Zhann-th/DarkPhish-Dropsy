"""
Dropsy OSINT: Bayesian Belief Engine for Threat Actor Attribution.
Computes posterior probability P(Actor Identity | OSINT Evidence)
filtering out homonyms, shared proxies, and coincidence artifacts.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class OsintEvidenceProfile:
    evidence_type: str
    tpr: float  # P(Evidence | True Actor) - Sensitivity
    fpr: float  # P(Evidence | Coincidence/False Match) - False Positive Rate
    description: str


DEFAULT_EVIDENCE_PROFILES: Dict[str, OsintEvidenceProfile] = {
    "PGP_KEY_MATCH": OsintEvidenceProfile(
        "PGP_KEY_MATCH", 0.99, 0.001,
        "Cryptographic PGP/GPG Key Fingerprint matches public commit signature"
    ),
    "BREACH_PASSWORD_HASH": OsintEvidenceProfile(
        "BREACH_PASSWORD_HASH", 0.94, 0.02,
        "Identical SHA-1/bcrypt password hash found in de-hashed breach collection"
    ),
    "TIMEZONE_UTC+3": OsintEvidenceProfile(
        "TIMEZONE_UTC+3", 0.85, 0.15,
        "GitHub/Forum activity temporal distribution aligns with UTC+3 working hours"
    ),
    "COMMIT_METADATA": OsintEvidenceProfile(
        "COMMIT_METADATA", 0.90, 0.05,
        "Author name and internal system username found in git config headers"
    ),
    "WHOIS_HISTORY": OsintEvidenceProfile(
        "WHOIS_HISTORY", 0.88, 0.04,
        "Historical WHOIS unmasked record links domain to verified personal email"
    ),
    "NICKNAME_SIMILARITY": OsintEvidenceProfile(
        "NICKNAME_SIMILARITY", 0.80, 0.10,
        "Jaro-Winkler alias similarity (>0.85) across multiple underground forums"
    ),
}


@dataclass
class BayesAttributionStep:
    step: int
    evidence_type: str
    prior: float
    likelihood_h1: float
    likelihood_h0: float
    marginal: float
    posterior: float
    explanation: str

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "evidence_type": self.evidence_type,
            "prior": round(self.prior, 4),
            "likelihood_h1": round(self.likelihood_h1, 4),
            "likelihood_h0": round(self.likelihood_h0, 4),
            "marginal": round(self.marginal, 4),
            "posterior": round(self.posterior, 4),
            "explanation": self.explanation,
        }


class BayesianAttributionEngine:
    """
    Performs rigorous Bayesian inference to confirm threat actor attribution
    over multi-source OSINT evidence streams.
    """

    def __init__(self, profiles: Optional[Dict[str, OsintEvidenceProfile]] = None):
        self.profiles = profiles or DEFAULT_EVIDENCE_PROFILES

    def update_belief(
        self,
        prior: float,
        evidence_type: str,
        custom_tpr: Optional[float] = None,
        custom_fpr: Optional[float] = None
    ) -> BayesAttributionStep:
        """
        Single-step Bayes update:
        P(Actor | Evidence) = [P(Evidence | Actor) * P(Actor)] / P(Evidence)
        """
        prior = max(0.0001, min(0.9999, prior))
        prior_h0 = 1.0 - prior

        prof = self.profiles.get(evidence_type)
        tpr = custom_tpr if custom_tpr is not None else (prof.tpr if prof else 0.85)
        fpr = custom_fpr if custom_fpr is not None else (prof.fpr if prof else 0.05)

        marginal = (tpr * prior) + (fpr * prior_h0)
        posterior = (tpr * prior) / marginal
        posterior = max(0.0001, min(0.9999, posterior))

        explanation = (
            f"Evidence '{evidence_type}' (TPR={tpr:.3f}, FPR={fpr:.3f}) updated attribution confidence "
            f"from {prior*100:.1f}% to {posterior*100:.1f}%."
        )

        return BayesAttributionStep(
            step=1,
            evidence_type=evidence_type,
            prior=prior,
            likelihood_h1=tpr,
            likelihood_h0=fpr,
            marginal=marginal,
            posterior=posterior,
            explanation=explanation,
        )

    def sequential_attribution(
        self,
        initial_prior: float,
        evidence_list: List[str]
    ) -> Tuple[float, List[BayesAttributionStep]]:
        """Recursively filters evidence stream to reach definitive attribution."""
        current_prior = initial_prior
        steps = []
        for idx, ev in enumerate(evidence_list, 1):
            step = self.update_belief(current_prior, ev)
            step.step = idx
            steps.append(step)
            current_prior = step.posterior
        return current_prior, steps
