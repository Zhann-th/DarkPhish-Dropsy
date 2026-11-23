from unittest import TestCase
from dropsy.core.darkphish_course import GRAPH, analyze, lower_bounds, recommend, search, update_belief


class SearchTests(TestCase):
    def test_four_routes(self):
        routes = analyze()["routes"]
        self.assertEqual({method: (route["cost"], len(route["trace"])) for method, route in routes.items()},
                         {"bfs": (10, 6), "dfs": (13, 5), "ucs": (6, 7), "astar": (6, 6)})

    def test_consistency_on_every_fixture_edge(self):
        h = lower_bounds(GRAPH, "decision")
        self.assertEqual(h["decision"], 0)
        for source, arcs in GRAPH.items():
            for target, weight in arcs:
                self.assertLessEqual(h[source], weight + h[target])

    def test_disconnected_goal(self):
        for method in ("bfs", "dfs", "ucs", "astar"):
            self.assertEqual(search(method, {"report": (), "decision": ()})["path"], ())


class PipelineTests(TestCase):
    def test_bayes_fraction(self):
        self.assertAlmostEqual(analyze()["belief"]["posterior"], 17/21)

    def test_no_observations_keeps_prior(self):
        self.assertEqual(update_belief((), {})["posterior"], .10)

    def test_route_and_missing_observation_change_decision(self):
        self.assertEqual(analyze()["decision"]["recommended"], "Escalate to incident team")
        self.assertEqual(analyze("bfs")["decision"]["recommended"], "Close as low priority")
        self.assertEqual(analyze(scenario="missing")["decision"]["recommended"], "Request manual review")

    def test_manual_review_fixed_point(self):
        result = recommend(2/7)
        self.assertAlmostEqual(result["value"], -1/(1-.9*.25))
        self.assertLess(result["delta"], result["epsilon"])


class WebsiteModeTests(TestCase):
    @staticmethod
    def snapshot(status=404, linked=True):
        from dropsy.core.audit import build_snapshot
        root, target = "https://example.org/", "https://example.org/help"
        return build_snapshot({
            "target_type": "REMOTE_NETWORK", "source": "observed", "scope": root,
            "pages": [{"url": root, "path": "/", "status": 200, "title": "Home"},
                      {"url": target, "path": "/help", "status": status, "title": "Help"}],
            "page_links": [{"source": root, "target": target}] if linked else [],
        })

    def test_live_snapshot_drives_route_probability_and_policy(self):
        from dropsy.core.darkphish_course import analyze_website
        result = analyze_website(self.snapshot(), "astar", "page-1")
        control = analyze_website(self.snapshot(200), "astar", "page-1")
        self.assertEqual(result["routes"]["astar"]["cost"], 2)
        self.assertEqual(control["routes"]["astar"]["cost"], 1)
        self.assertGreater(result["belief"]["posterior"], control["belief"]["posterior"])
        self.assertEqual(result["decision"]["recommended"], "Request manual review")
        self.assertEqual(control["decision"]["recommended"], "Close as low priority")

    def test_unreachable_destination_and_zero_hop_route(self):
        from dropsy.core.darkphish_course import analyze_website
        snapshot = self.snapshot(linked=False)
        result = analyze_website(snapshot)
        self.assertEqual(result["routes"]["astar"]["path"], ("page-0",))
        self.assertEqual(result["routes"]["astar"]["cost"], 0)
        with self.assertRaisesRegex(ValueError, "linked"):
            analyze_website(snapshot, destination="page-1")
