"""
Dropsy OSINT: Autonomous Investigation Policy via Bellman MDP.
Solves sequential decision making to guide intelligence pivots,
balancing intelligence discovery against OpSec exposure risk and API quotas.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import copy


STATES = [
    "S0_INITIAL_SEED",          # Initial unverified indicator (domain / wallet)
    "S1_INFRA_UNVEILED",        # Hosting, SSL SANs, and IP infrastructure mapped
    "S2_PERSONA_ISOLATED",      # Developer email, aliases, and code repos linked
    "S3_IDENTITY_CONFIRMED",    # High-confidence Bayesian attribution achieved
    "S4_DOSSIER_COMPLETE",      # Absorbing terminal state: intelligence brief sealed
]

ACTIONS = [
    "A0_PASSIVE_RECON",         # Certificate Transparency & DNS (0 OpSec risk, low cost)
    "A1_BREACH_QUERY",          # De-hashed breach database query (safe, high info gain)
    "A2_SOCIAL_CORRELATE",      # GitHub/Telegram actor footprint crawl (moderate OpSec risk)
    "A3_ACTIVE_BANNER_GRAB",    # Direct port probe / Shodan banner grab (high OpSec exposure risk)
]


@dataclass
class OsintExecutableCommand:
    action: str
    target: str
    tool_name: str
    cli_command: str
    description: str

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "target": self.target,
            "tool_name": self.tool_name,
            "cli_command": self.cli_command,
            "description": self.description,
        }


@dataclass
class OsintMDPResult:
    converged: bool
    iterations: int
    gamma: float
    epsilon: float
    optimal_values: Dict[str, float]
    optimal_policy: Dict[str, str]
    q_table: Dict[str, Dict[str, float]]
    recommended_action: str
    rationale: str
    generated_commands: List[OsintExecutableCommand] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "converged": self.converged,
            "iterations": self.iterations,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "optimal_values": {s: round(v, 2) for s, v in self.optimal_values.items()},
            "optimal_policy": self.optimal_policy,
            "q_table": {s: {a: round(v, 2) for a, v in acts.items()} for s, acts in self.q_table.items()},
            "recommended_action": self.recommended_action,
            "rationale": self.rationale,
            "generated_commands": [c.to_dict() for c in self.generated_commands],
        }


class InvestigationPlannerMDP:
    """
    Autonomous OSINT Investigation Planner formulated as MDP <S, A, P, R, gamma>.
    """

    def __init__(self, gamma: float = 0.90, epsilon: float = 0.001):
        self.gamma = gamma
        self.epsilon = epsilon
        self.states = STATES
        self.actions = ACTIONS

    def build_transition_model(self, bayesian_belief: float) -> Dict[str, Dict[str, Dict[str, float]]]:
        """P(s' | s, a) parameterized by current attribution certainty."""
        P: Dict[str, Dict[str, Dict[str, float]]] = {
            s: {a: {s_prime: 0.0 for s_prime in self.states} for a in self.actions}
            for s in self.states
        }
        confidence = max(0.1, min(0.99, bayesian_belief))

        # --- S0_INITIAL_SEED ---
        P["S0_INITIAL_SEED"]["A0_PASSIVE_RECON"]["S1_INFRA_UNVEILED"] = 0.85
        P["S0_INITIAL_SEED"]["A0_PASSIVE_RECON"]["S0_INITIAL_SEED"] = 0.15

        P["S0_INITIAL_SEED"]["A1_BREACH_QUERY"]["S1_INFRA_UNVEILED"] = 0.40
        P["S0_INITIAL_SEED"]["A1_BREACH_QUERY"]["S0_INITIAL_SEED"] = 0.60

        P["S0_INITIAL_SEED"]["A2_SOCIAL_CORRELATE"]["S1_INFRA_UNVEILED"] = 0.50
        P["S0_INITIAL_SEED"]["A2_SOCIAL_CORRELATE"]["S0_INITIAL_SEED"] = 0.50

        P["S0_INITIAL_SEED"]["A3_ACTIVE_BANNER_GRAB"]["S1_INFRA_UNVEILED"] = 0.95
        P["S0_INITIAL_SEED"]["A3_ACTIVE_BANNER_GRAB"]["S0_INITIAL_SEED"] = 0.05

        # --- S1_INFRA_UNVEILED ---
        P["S1_INFRA_UNVEILED"]["A0_PASSIVE_RECON"]["S1_INFRA_UNVEILED"] = 0.60
        P["S1_INFRA_UNVEILED"]["A0_PASSIVE_RECON"]["S2_PERSONA_ISOLATED"] = 0.40

        # Breach query is highly effective when domain/email are known
        P["S1_INFRA_UNVEILED"]["A1_BREACH_QUERY"]["S2_PERSONA_ISOLATED"] = 0.90
        P["S1_INFRA_UNVEILED"]["A1_BREACH_QUERY"]["S1_INFRA_UNVEILED"] = 0.10

        P["S1_INFRA_UNVEILED"]["A2_SOCIAL_CORRELATE"]["S2_PERSONA_ISOLATED"] = 0.75
        P["S1_INFRA_UNVEILED"]["A2_SOCIAL_CORRELATE"]["S1_INFRA_UNVEILED"] = 0.25

        P["S1_INFRA_UNVEILED"]["A3_ACTIVE_BANNER_GRAB"]["S2_PERSONA_ISOLATED"] = 0.80
        P["S1_INFRA_UNVEILED"]["A3_ACTIVE_BANNER_GRAB"]["S1_INFRA_UNVEILED"] = 0.20

        # --- S2_PERSONA_ISOLATED ---
        P["S2_PERSONA_ISOLATED"]["A0_PASSIVE_RECON"]["S2_PERSONA_ISOLATED"] = 0.80
        P["S2_PERSONA_ISOLATED"]["A0_PASSIVE_RECON"]["S3_IDENTITY_CONFIRMED"] = 0.20

        P["S2_PERSONA_ISOLATED"]["A1_BREACH_QUERY"]["S3_IDENTITY_CONFIRMED"] = min(0.95, confidence + 0.1)
        P["S2_PERSONA_ISOLATED"]["A1_BREACH_QUERY"]["S2_PERSONA_ISOLATED"] = 1.0 - P["S2_PERSONA_ISOLATED"]["A1_BREACH_QUERY"]["S3_IDENTITY_CONFIRMED"]

        P["S2_PERSONA_ISOLATED"]["A2_SOCIAL_CORRELATE"]["S3_IDENTITY_CONFIRMED"] = 0.85
        P["S2_PERSONA_ISOLATED"]["A2_SOCIAL_CORRELATE"]["S2_PERSONA_ISOLATED"] = 0.15

        P["S2_PERSONA_ISOLATED"]["A3_ACTIVE_BANNER_GRAB"]["S3_IDENTITY_CONFIRMED"] = 0.40
        P["S2_PERSONA_ISOLATED"]["A3_ACTIVE_BANNER_GRAB"]["S2_PERSONA_ISOLATED"] = 0.60

        # --- S3_IDENTITY_CONFIRMED ---
        for a in self.actions:
            P["S3_IDENTITY_CONFIRMED"][a]["S4_DOSSIER_COMPLETE"] = 0.98
            P["S3_IDENTITY_CONFIRMED"][a]["S3_IDENTITY_CONFIRMED"] = 0.02

        # --- S4_DOSSIER_COMPLETE (Terminal absorbing state) ---
        for a in self.actions:
            P["S4_DOSSIER_COMPLETE"][a]["S4_DOSSIER_COMPLETE"] = 1.0

        return P

    def build_reward_model(self) -> Dict[str, Dict[str, float]]:
        """Balances intelligence gain against OpSec exposure costs."""
        return {
            "S0_INITIAL_SEED": {
                "A0_PASSIVE_RECON": 30.0,       # Best first move: 100% stealthy Certificate Transparency query
                "A1_BREACH_QUERY": 10.0,        # Premature
                "A2_SOCIAL_CORRELATE": 5.0,
                "A3_ACTIVE_BANNER_GRAB": -40.0, # High OpSec burn: premature active scan alerts target!
            },
            "S1_INFRA_UNVEILED": {
                "A0_PASSIVE_RECON": 15.0,
                "A1_BREACH_QUERY": 45.0,        # Optimal: correlate WHOIS email with breach dumps
                "A2_SOCIAL_CORRELATE": 35.0,     # Strong pivot
                "A3_ACTIVE_BANNER_GRAB": -15.0,
            },
            "S2_PERSONA_ISOLATED": {
                "A0_PASSIVE_RECON": 5.0,
                "A1_BREACH_QUERY": 30.0,
                "A2_SOCIAL_CORRELATE": 50.0,     # Optimal: cross-examine commit GPG and social handles
                "A3_ACTIVE_BANNER_GRAB": -30.0,
            },
            "S3_IDENTITY_CONFIRMED": {
                "A0_PASSIVE_RECON": 80.0,       # Assemble final dossier
                "A1_BREACH_QUERY": 80.0,
                "A2_SOCIAL_CORRELATE": 80.0,
                "A3_ACTIVE_BANNER_GRAB": 80.0,
            },
            "S4_DOSSIER_COMPLETE": {
                "A0_PASSIVE_RECON": 0.0,
                "A1_BREACH_QUERY": 0.0,
                "A2_SOCIAL_CORRELATE": 0.0,
                "A3_ACTIVE_BANNER_GRAB": 0.0,
            },
        }

    def generate_commands(self, target_seed: str, action: str) -> List[OsintExecutableCommand]:
        """Generates concrete executable OSINT investigation commands."""
        cmds = []
        if action == "A0_PASSIVE_RECON":
            cmds.append(OsintExecutableCommand(
                action=action, target=target_seed, tool_name="crt.sh API",
                cli_command=f"curl -s 'https://crt.sh/?q={target_seed}&output=json' | jq '.[].name_value' | sort -u",
                description="Query Certificate Transparency log to uncover hidden subdomains and SSL SANs."
            ))
            cmds.append(OsintExecutableCommand(
                action=action, target=target_seed, tool_name="DNS TXT/MX Recon",
                cli_command=f"dig +noall +answer {target_seed} ANY",
                description="Passive DNS interrogation to extract mail servers and verification records."
            ))
        elif action == "A1_BREACH_QUERY":
            cmds.append(OsintExecutableCommand(
                action=action, target=target_seed, tool_name="HaveIBeenPwned API",
                cli_command=f"curl -s -H 'hibp-api-key: $HIBP_KEY' 'https://haveibeenpwned.com/api/v3/breachedaccount/{target_seed}'",
                description="Check historical data breach dumps for leaked password hashes and registrations."
            ))
        elif action == "A2_SOCIAL_CORRELATE":
            cmds.append(OsintExecutableCommand(
                action=action, target=target_seed, tool_name="GitHub Events API",
                cli_command=f"gh api 'users/{target_seed}/events/public' --jq '.[].payload.commits[].author'",
                description="Extract public commit metadata, GPG key fingerprints, and author timezone cadence."
            ))
        elif action == "A3_ACTIVE_BANNER_GRAB":
            cmds.append(OsintExecutableCommand(
                action=action, target=target_seed, tool_name="Shodan Host Search",
                cli_command=f"shodan host {target_seed}",
                description="Active port scan banner grabbing to fingerprint internal server software and hostnames."
            ))
        return cmds

    def solve_value_iteration(
        self,
        bayesian_belief: float = 0.5,
        current_state: str = "S0_INITIAL_SEED",
        target_seed: str = "chase-secure-verification.xyz"
    ) -> OsintMDPResult:
        """Runs Bellman Value Iteration until convergence."""
        P = self.build_transition_model(bayesian_belief)
        R = self.build_reward_model()

        V: Dict[str, float] = {s: 0.0 for s in self.states}
        max_iter = 250
        iteration = 0

        while iteration < max_iter:
            iteration += 1
            delta = 0.0
            V_new = copy.deepcopy(V)

            for s in self.states:
                if s == "S4_DOSSIER_COMPLETE":
                    V_new[s] = 0.0
                    continue
                q_vals = [
                    R[s][a] + (self.gamma * sum(P[s][a][s_prime] * V[s_prime] for s_prime in self.states))
                    for a in self.actions
                ]
                best_v = max(q_vals)
                delta = max(delta, abs(best_v - V[s]))
                V_new[s] = best_v

            V = V_new
            if delta < self.epsilon:
                break

        optimal_policy = {}
        q_table = {s: {} for s in self.states}
        for s in self.states:
            best_a = self.actions[0]
            best_q = float("-inf")
            for a in self.actions:
                val = R[s][a] + (self.gamma * sum(P[s][a][s_prime] * V[s_prime] for s_prime in self.states))
                q_table[s][a] = val
                if val > best_q:
                    best_q = val
                    best_a = a
            optimal_policy[s] = best_a

        rec_action = optimal_policy.get(current_state, "A0_PASSIVE_RECON")
        commands = self.generate_commands(target_seed, rec_action)

        rationale = (
            f"At state {current_state} (Bayes Attribution Confidence: {bayesian_belief*100:.1f}%), "
            f"Bellman value iteration converged in {iteration} steps. Optimal pivot is '{rec_action}' "
            f"(Expected Utility Q = {q_table[current_state][rec_action]:.1f}). Generated {len(commands)} actionable OSINT commands."
        )

        return OsintMDPResult(
            converged=(iteration < max_iter),
            iterations=iteration,
            gamma=self.gamma,
            epsilon=self.epsilon,
            optimal_values=V,
            optimal_policy=optimal_policy,
            q_table=q_table,
            recommended_action=rec_action,
            rationale=rationale,
            generated_commands=commands,
        )
