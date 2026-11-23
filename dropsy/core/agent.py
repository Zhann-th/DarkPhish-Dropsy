"""
Dropsy OSINT: Unified Autonomous Threat Intelligence Agent.
Orchestrates Entity Graph Search (A*), Bayesian Identity Attribution,
and Bellman Value Iteration MDP into an end-to-end OSINT investigation workflow.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from dropsy.core.entity_graph import OsintKnowledgeGraph, OsintEntity
from dropsy.core.search_engine import OsintPathSearchEngine, SearchResult
from dropsy.core.bayes_engine import BayesianAttributionEngine, BayesAttributionStep
from dropsy.core.mdp_engine import InvestigationPlannerMDP, OsintMDPResult, OsintExecutableCommand
from dropsy.data.osint_cases import build_darkphish_investigation_case, AVAILABLE_CASES


@dataclass
class OsintInvestigationReport:
    case_id: str
    case_title: str
    seed_indicator: str
    target_persona: str
    pivot_search_result: SearchResult
    bayesian_steps: List[BayesAttributionStep]
    final_attribution_confidence: float
    mdp_plan: OsintMDPResult
    generated_commands: List[OsintExecutableCommand]
    attribution_confirmed: bool
    intelligence_dossier_summary: str

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "case_title": self.case_title,
            "seed_indicator": self.seed_indicator,
            "target_persona": self.target_persona,
            "pivot_search_result": self.pivot_search_result.to_dict(),
            "bayesian_steps": [s.to_dict() for s in self.bayesian_steps],
            "final_attribution_confidence": round(self.final_attribution_confidence, 4),
            "mdp_plan": self.mdp_plan.to_dict(),
            "generated_commands": [c.to_dict() for c in self.generated_commands],
            "attribution_confirmed": self.attribution_confirmed,
            "intelligence_dossier_summary": self.intelligence_dossier_summary,
        }


class DropsyInvestigatorAgent:
    """
    Autonomous OSINT Investigator integrating A*, Bayes, and Bellman MDP.
    """

    def __init__(self, graph: Optional[OsintKnowledgeGraph] = None):
        self.graph = graph or build_darkphish_investigation_case()
        self.search_engine = OsintPathSearchEngine(self.graph)
        self.bayes_engine = BayesianAttributionEngine()
        self.mdp_engine = InvestigationPlannerMDP(gamma=0.90, epsilon=0.001)

    def run_investigation(
        self,
        seed_id: str = "domain_phish_01",
        target_id: str = "actor_alex_perry",
        case_title: str = "Operation DarkPhish"
    ) -> OsintInvestigationReport:
        """Executes full autonomous OSINT investigation cycle."""
        # Step 1: A* Search across entity graph to find shortest attribution path
        search_res = self.search_engine.a_star_search(seed_id, target_id)

        target_entity = self.graph.entities.get(target_id)
        evidence_list = target_entity.evidence_tags if target_entity else ["PGP_KEY_MATCH", "BREACH_PASSWORD_HASH", "TIMEZONE_UTC+3"]

        # Step 2: Bayesian Belief Update on identity attribution
        initial_prior = self.graph.entities[seed_id].confidence if seed_id in self.graph.entities else 0.10
        final_conf, bayes_steps = self.bayes_engine.sequential_attribution(initial_prior, evidence_list)

        if target_entity:
            target_entity.confidence = final_conf

        # Step 3: Determine state and solve MDP
        if final_conf < 0.30:
            mdp_state = "S0_INITIAL_SEED"
        elif final_conf < 0.65:
            mdp_state = "S1_INFRA_UNVEILED"
        elif final_conf < 0.90:
            mdp_state = "S2_PERSONA_ISOLATED"
        else:
            mdp_state = "S3_IDENTITY_CONFIRMED"

        mdp_res = self.mdp_engine.solve_value_iteration(
            bayesian_belief=final_conf,
            current_state=mdp_state,
            target_seed=self.graph.entities[seed_id].name if seed_id in self.graph.entities else seed_id
        )

        attribution_confirmed = (final_conf >= 0.90 and search_res.path_found)

        dossier = (
            f"Dropsy Investigation [{case_title}]: Traced seed '{self.graph.entities[seed_id].name}' "
            f"across {len(search_res.optimal_path)} verified pivot hops to target '{self.graph.entities[target_id].name}'. "
            f"Bayesian attribution fused {len(evidence_list)} independent OSINT artifacts, confirming identity "
            f"at {final_conf*100:.1f}% confidence. Bellman MDP formulated optimal next move '{mdp_res.recommended_action}' "
            f"with {len(mdp_res.generated_commands)} automated recon commands. Status: {'ATTRIBUTION DEANONYMIZED' if attribution_confirmed else 'PENDING'}."
        )

        return OsintInvestigationReport(
            case_id="darkphish",
            case_title=case_title,
            seed_indicator=seed_id,
            target_persona=target_id,
            pivot_search_result=search_res,
            bayesian_steps=bayes_steps,
            final_attribution_confidence=final_conf,
            mdp_plan=mdp_res,
            generated_commands=mdp_res.generated_commands,
            attribution_confirmed=attribution_confirmed,
            intelligence_dossier_summary=dossier
        )
