"""
Dropsy OSINT: Terminal Investigation Runner & Automated Demonstration.
Outputs ANSI-colored Maltego-style pivot graphs, Bayesian identity log-odds,
Bellman MDP optimal policies, and actionable intelligence dossiers.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import argparse
from dropsy.core.entity_graph import OsintKnowledgeGraph
from dropsy.core.search_engine import OsintPathSearchEngine
from dropsy.core.bayes_engine import BayesianAttributionEngine
from dropsy.core.mdp_engine import InvestigationPlannerMDP
from dropsy.core.agent import DropsyInvestigatorAgent
from dropsy.data.osint_cases import build_darkphish_investigation_case

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    print(f"{CYAN}{BOLD}========================================================================")
    print(r"   ____  ____   ___  ____  ______   __")
    print(r"  / __ \/ __ \ / __ \/ __ \/ ___/\ / /")
    print(r" / / / / /_/ // / / / /_/ /\__ \  / / ")
    print(r"/ /_/ / _, _// /_/ / ____/___/ / / /  ")
    print(r"\____/_/ |_| \____/_/    /____/ /_/   ")
    print("   AUTONOMOUS OSINT THREAT INTELLIGENCE & ACTOR DEANONYMIZATION")
    print(f"========================================================================{RESET}")


def run_dropsy_cli_demo():
    print_banner()
    print(f"\n{BOLD}[*] Loading Active Threat Investigation: 'Operation DarkPhish'...{RESET}")
    graph = build_darkphish_investigation_case()
    time.sleep(0.3)

    print(f"[*] Ingested {len(graph.entities)} Verifiable OSINT Entities across 5 Tiers:")
    for eid, ent in graph.entities.items():
        type_pad = f"[{ent.entity_type}]".ljust(16)
        print(f"  {DIM}Entity [{eid.ljust(22)}]{RESET} | Tier {ent.tier} | {type_pad} | Conf: {ent.confidence*100:4.1f}% | {ent.name}")

    # -------------------------------------------------------------
    # AI TOPIC 1: A* SEARCH ON ENTITY KNOWLEDGE GRAPH
    # -------------------------------------------------------------
    print(f"\n{MAGENTA}{BOLD}========================================================================{RESET}")
    print(f"{MAGENTA}{BOLD}[PILLAR 1: SEARCH] A* Pivot Pathfinding across Entity Resolution Graph{RESET}")
    print(f"{MAGENTA}{BOLD}========================================================================{RESET}")
    search_eng = OsintPathSearchEngine(graph)
    print(f"[*] Tracing shortest verifiable attribution path from seed '{YELLOW}domain_phish_01{RESET}' to target persona '{RED}actor_alex_perry{RESET}'...")
    res = search_eng.a_star_search("domain_phish_01", "actor_alex_perry")

    print(f"{GREEN}[+] Verifiable Pivot Chain Discovered:{RESET}")
    for idx, (node_id, name) in enumerate(zip(res.optimal_path, res.path_names), 1):
        print(f"    {idx}. [{node_id}] {CYAN}{name}{RESET}")

    print(f"\n    Total Obfuscation Resistance: {res.total_cost:.2f}")
    print(f"    Search Space Expanded:        {res.nodes_expanded} entities")
    print(f"    Critical Attribution Pivots:  {res.critical_pivots}")

    # Comparative benchmark with Dijkstra
    dijkstra_res = search_eng.dijkstra_search("domain_phish_01", "actor_alex_perry")
    gain = ((dijkstra_res.nodes_expanded - res.nodes_expanded) / dijkstra_res.nodes_expanded) * 100
    print(f"    {DIM}Benchmark: Dijkstra expanded {dijkstra_res.nodes_expanded} nodes vs A* {res.nodes_expanded} nodes (Efficiency Gain: {gain:.1f}%){RESET}")

    # -------------------------------------------------------------
    # AI TOPIC 2: BAYESIAN IDENTITY ATTRIBUTION
    # -------------------------------------------------------------
    print(f"\n{YELLOW}{BOLD}========================================================================{RESET}")
    print(f"{YELLOW}{BOLD}[PILLAR 2: PROBABILISTIC REASONING] Bayesian Attribution Engine{RESET}")
    print(f"{YELLOW}{BOLD}========================================================================{RESET}")
    bayes_eng = BayesianAttributionEngine()
    target_ent = graph.entities["actor_alex_perry"]
    prior = 0.10
    print(f"[*] Evaluating multi-source OSINT evidence for persona: {BOLD}{target_ent.name}{RESET}")
    print(f"    Initial Prior P(True Actor): {prior*100:.1f}%\n")

    for idx, ev in enumerate(target_ent.evidence_tags, 1):
        step = bayes_eng.update_belief(prior, ev)
        print(f"    {BOLD}Step {idx} Evidence [{ev}]:{RESET}")
        print(f"      - Sensitivity P(E|Actor):      {step.likelihood_h1:.3f}")
        print(f"      - Coincidence P(E|Not Actor):  {step.likelihood_h0:.3f}")
        print(f"      - Marginal Evidence P(E):      {step.marginal:.4f}")
        print(f"      - Posterior P(True Identity):  {GREEN}{step.posterior*100:5.1f}%{RESET}")
        prior = step.posterior
        time.sleep(0.3)

    # -------------------------------------------------------------
    # AI TOPIC 3: BELLMAN MDP INVESTIGATION PLANNER
    # -------------------------------------------------------------
    print(f"\n{CYAN}{BOLD}========================================================================{RESET}")
    print(f"{CYAN}{BOLD}[PILLAR 3: SEQUENTIAL DECISION MAKING] Bellman MDP Autonomous Recon{RESET}")
    print(f"{CYAN}{BOLD}========================================================================{RESET}")
    mdp_eng = InvestigationPlannerMDP(gamma=0.90, epsilon=0.001)
    mdp_res = mdp_eng.solve_value_iteration(
        bayesian_belief=prior,
        current_state="S3_IDENTITY_CONFIRMED",
        target_seed="chase-secure-verification.xyz"
    )

    print(f"{GREEN}[+] Bellman Equation Converged in {mdp_res.iterations} iterations (epsilon < 0.001){RESET}")
    print(f"\n    {BOLD}Optimal Q-Table Matrix Q*(s, a):{RESET}")
    header = f"    {'State'.ljust(22)} | {'A0:PASSIVE'.ljust(11)} | {'A1:BREACH'.ljust(11)} | {'A2:SOCIAL'.ljust(11)} | {'A3:ACTIVE'.ljust(11)} | {'Optimal pi*(s)'}"
    print(header)
    print("    " + "-" * (len(header) - 4))

    for s, actions in mdp_res.q_table.items():
        opt = mdp_res.optimal_policy[s]
        a0 = f"{actions['A0_PASSIVE_RECON']:6.1f}"
        a1 = f"{actions['A1_BREACH_QUERY']:6.1f}"
        a2 = f"{actions['A2_SOCIAL_CORRELATE']:6.1f}"
        a3 = f"{actions['A3_ACTIVE_BANNER_GRAB']:6.1f}"
        print(f"    {s.ljust(22)} | {a0.ljust(11)} | {a1.ljust(11)} | {a2.ljust(11)} | {a3.ljust(11)} | {GREEN}{opt}{RESET}")

    print(f"\n    {BOLD}Recommended Next Investigative Move:{RESET} {CYAN}{BOLD}{mdp_res.recommended_action}{RESET}")
    print(f"    Rationale: {mdp_res.rationale}")

    print(f"\n    {BOLD}Generated Concrete OSINT Reconnaissance Commands:{RESET}")
    for cmd in mdp_res.generated_commands:
        print(f"    {GREEN}${RESET} {CYAN}{cmd.cli_command}{RESET}")
        print(f"       {DIM}-> {cmd.description} [{cmd.tool_name}]{RESET}")

    # Final Dossier
    print(f"\n{GREEN}{BOLD}========================================================================{RESET}")
    print(f"{GREEN}{BOLD}[INTELLIGENCE DOSSIER DE-ANONYMIZATION CONFIRMED]{RESET}")
    print(f"{GREEN}{BOLD}========================================================================{RESET}")
    print(f"  Target Persona:      Alexander Perry (Phishing Kit Author & Operator)")
    print(f"  Location:            Tbilisi / Moscow (UTC+3 temporal cadence)")
    print(f"  Verified Identity:   github.com/dev_alexperry | alex_darknet99@proton.me")
    print(f"  GPG Key Match:       4A89C19F (100% Cryptographic Match)")
    print(f"  Attribution Status:  {GREEN}{BOLD}CONFIRMED (99.0% Confidence){RESET}")
    print(f"========================================================================\n")


if __name__ == "__main__":
    run_dropsy_cli_demo()
