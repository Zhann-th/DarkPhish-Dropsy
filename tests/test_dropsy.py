"""
Unit and Integration Tests for Dropsy AI OSINT System.
Tests Search (A*, Dijkstra), Bayesian Attribution, Bellman MDP, and Agent Loop.
"""

import unittest
from dropsy.core.entity_graph import OsintKnowledgeGraph, OsintEntity, OsintLink
from dropsy.core.search_engine import OsintPathSearchEngine
from dropsy.core.bayes_engine import BayesianAttributionEngine
from dropsy.core.mdp_engine import InvestigationPlannerMDP
from dropsy.core.agent import DropsyInvestigatorAgent
from dropsy.data.osint_cases import build_darkphish_investigation_case


class TestDropsySearch(unittest.TestCase):
    def setUp(self):
        self.graph = build_darkphish_investigation_case()
        self.search = OsintPathSearchEngine(self.graph)

    def test_admissible_heuristic(self):
        # Seed tier 0, Target tier 4 -> h(n) = (4 - 0) * 1.5 = 6.0
        h = self.search.admissible_heuristic("domain_phish_01", "actor_alex_perry")
        self.assertEqual(h, 6.0)

    def test_a_star_path_finding(self):
        res = self.search.a_star_search("domain_phish_01", "actor_alex_perry")
        self.assertTrue(res.path_found)
        self.assertEqual(res.optimal_path[0], "domain_phish_01")
        self.assertEqual(res.optimal_path[-1], "actor_alex_perry")
        self.assertGreater(res.total_cost, 0.0)

    def test_a_star_vs_dijkstra_nodes_expanded(self):
        a_star_res = self.search.a_star_search("domain_phish_01", "actor_alex_perry")
        dijkstra_res = self.search.dijkstra_search("domain_phish_01", "actor_alex_perry")
        self.assertTrue(a_star_res.path_found)
        self.assertTrue(dijkstra_res.path_found)
        self.assertAlmostEqual(a_star_res.total_cost, dijkstra_res.total_cost, places=2)
        # A* expands fewer or equal nodes
        self.assertLessEqual(a_star_res.nodes_expanded, dijkstra_res.nodes_expanded)


class TestDropsyBayes(unittest.TestCase):
    def setUp(self):
        self.bayes = BayesianAttributionEngine()

    def test_single_shot_bayes_calculation(self):
        # Prior = 0.10, TPR = 0.99, FPR = 0.001 (PGP Match)
        # Marginal = 0.99 * 0.10 + 0.001 * 0.90 = 0.099 + 0.0009 = 0.0999
        # Posterior = 0.099 / 0.0999 = 0.99099...
        step = self.bayes.update_belief(0.10, "PGP_KEY_MATCH")
        expected_posterior = 0.099 / 0.0999
        self.assertAlmostEqual(step.posterior, expected_posterior, places=4)

    def test_sequential_attribution_accumulation(self):
        evidence = ["PGP_KEY_MATCH", "BREACH_PASSWORD_HASH", "TIMEZONE_UTC+3"]
        final_conf, steps = self.bayes.sequential_attribution(0.10, evidence)
        self.assertEqual(len(steps), 3)
        self.assertGreater(final_conf, 0.95)

    def test_boundary_prior_safety(self):
        s0 = self.bayes.update_belief(0.0, "PGP_KEY_MATCH")
        self.assertTrue(0.0 < s0.posterior < 1.0)
        s1 = self.bayes.update_belief(1.0, "PGP_KEY_MATCH")
        self.assertTrue(0.0 < s1.posterior < 1.0)


class TestDropsyMDP(unittest.TestCase):
    def setUp(self):
        self.mdp = InvestigationPlannerMDP(gamma=0.90, epsilon=0.001)

    def test_bellman_convergence(self):
        res = self.mdp.solve_value_iteration(bayesian_belief=0.5, current_state="S0_INITIAL_SEED")
        self.assertTrue(res.converged)
        self.assertLess(res.iterations, 250)

    def test_policy_rationality(self):
        # At initial seed, safest move with 0 OpSec risk is Passive Recon
        res_seed = self.mdp.solve_value_iteration(bayesian_belief=0.1, current_state="S0_INITIAL_SEED")
        self.assertEqual(res_seed.optimal_policy["S0_INITIAL_SEED"], "A0_PASSIVE_RECON")

        # When persona is isolated, best move is social correlation
        res_persona = self.mdp.solve_value_iteration(bayesian_belief=0.75, current_state="S2_PERSONA_ISOLATED")
        self.assertEqual(res_persona.optimal_policy["S2_PERSONA_ISOLATED"], "A2_SOCIAL_CORRELATE")

    def test_command_generation(self):
        cmds = self.mdp.generate_commands("phish.com", "A0_PASSIVE_RECON")
        self.assertGreater(len(cmds), 0)
        self.assertTrue(any("crt.sh" in c.cli_command for c in cmds))


class TestDropsyAgentIntegration(unittest.TestCase):
    def test_full_investigation_lifecycle(self):
        agent = DropsyInvestigatorAgent()
        report = agent.run_investigation("domain_phish_01", "actor_alex_perry")
        self.assertTrue(report.attribution_confirmed)
        self.assertGreater(report.final_attribution_confidence, 0.90)
        self.assertGreater(len(report.pivot_search_result.optimal_path), 2)
        self.assertGreater(len(report.generated_commands), 0)


if __name__ == "__main__":
    unittest.main()
