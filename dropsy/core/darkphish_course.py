"""Shared AI Fundamentals pipeline for a fixture and observed website snapshots."""
import argparse
import json
from urllib.parse import urlsplit

from .audit import validate_snapshot
from collections import deque
from heapq import heappop, heappush
from itertools import count


LABELS = {
    "report": "Reported email",
    "queue": "Mail queue",
    "archive": "Mail archive",
    "reputation": "Allowlist lookup",
    "intake": "Header review",
    "analyst": "Analyst finding",
    "decision": "Triage decision",
}
GRAPH = {
    "report": (("queue", 1), ("reputation", 6), ("intake", 2)),
    "queue": (("archive", 2),),
    "archive": (("reputation", 6),),
    "reputation": (("decision", 4),),
    "intake": (("analyst", 2),),
    "analyst": (("decision", 2),),
    "decision": (),
}
ALGORITHMS = ("bfs", "dfs", "ucs", "astar")
SCENARIOS = {
    "complete": {"label": "All observations available", "signals": {
        "archive": ("Mail archive found no matching incident", .40, .65),
        "reputation": ("Host appears on a fixture allowlist", .35, .55),
        "intake": ("Header authentication signal failed", .72, .20),
        "analyst": ("Analyst found a synthetic credential prompt", .85, .08),
    }},
    "missing": {"label": "Analyst finding unavailable", "signals": {
        "archive": ("Mail archive found no matching incident", .40, .65),
        "reputation": ("Host appears on a fixture allowlist", .35, .55),
        "intake": ("Header authentication signal failed", .72, .20),
    }},
}


def lower_bounds(graph, goal):
    """Minimum hops to the goal times the minimum edge cost."""
    predecessors = {node: [] for node in graph}
    for source, arcs in graph.items():
        for target, _ in arcs:
            predecessors[target].append(source)
    min_cost = min((cost for arcs in graph.values() for _, cost in arcs), default=0)
    distances = {goal: 0}
    queue = deque([goal])
    while queue:
        current = queue.popleft()
        for candidate in predecessors[current]:
            if candidate not in distances:
                distances[candidate] = distances[current] + min_cost
                queue.append(candidate)
    return distances


def search(method, graph=GRAPH, start="report", goal="decision"):
    if method not in ALGORITHMS:
        raise ValueError("Unknown search method")
    if start not in graph or goal not in graph:
        raise ValueError("Unknown graph node")

    heuristics = lower_bounds(graph, goal) if method == "astar" else {}
    trace = []

    def log(node, cost):
        bound = heuristics.get(node, 0)
        trace.append({"node": node, "g": cost, "h": bound, "f": cost + bound})

    if method in {"bfs", "dfs"}:
        frontier = deque([(start, (start,), 0)])
        visited = set()
        while frontier:
            node, path, cost = frontier.popleft() if method == "bfs" else frontier.pop()
            if node in visited:
                continue
            visited.add(node)
            log(node, cost)
            if node == goal:
                return {"path": path, "cost": cost, "trace": trace}
            arcs = graph[node] if method == "bfs" else reversed(graph[node])
            for child, weight in arcs:
                if child not in visited:
                    frontier.append((child, (*path, child), cost + weight))
    else:
        tie = count()
        heap = [(heuristics.get(start, 0), next(tie), 0, start, (start,))]
        best = {start: 0}
        while heap:
            _, _, cost, node, path = heappop(heap)
            if cost != best[node]:
                continue
            log(node, cost)
            if node == goal:
                return {"path": path, "cost": cost, "trace": trace}
            for child, weight in graph[node]:
                candidate = cost + weight
                if candidate < best.get(child, float("inf")):
                    best[child] = candidate
                    priority = candidate + heuristics.get(child, 0)
                    heappush(heap, (priority, next(tie), candidate, child, (*path, child)))
    return {"path": (), "cost": None, "trace": trace}


def update_belief(path, signals, prior=.10):
    p = prior
    steps = []
    for node in path:
        if node not in signals:
            continue
        label, phishing, benign = signals[node]
        numerator = p * phishing
        marginal = numerator + (1 - p) * benign
        result = numerator / marginal
        steps.append({"node": node, "signal": label, "prior": p, "likelihood_phishing": phishing,
                      "likelihood_benign": benign, "marginal": marginal, "posterior": result})
        p = result
    return {"initial": prior, "posterior": p, "steps": steps}


def recommend(p, gamma=.90, epsilon=1e-8, escalation="Escalate to incident team"):
    """Value iteration for pending and resolved states, conditioned on p."""
    table = {
        "Close as low priority": {"hypothesis": -12, "alternative": 2, "pending_probability": 0},
        "Request manual review": {"hypothesis": -1, "alternative": -1, "pending_probability": .25},
        escalation: {"hypothesis": 6, "alternative": -6, "pending_probability": 0},
    }
    for action in table.values():
        action["reward"] = p * action["hypothesis"] + (1 - p) * action["alternative"]

    def scores(value):
        return {name: row["reward"] + gamma * row["pending_probability"] * value
                for name, row in table.items()}

    value = 0
    for iteration in range(1, 201):
        candidate = max(scores(value).values())
        delta = abs(candidate - value)
        value = candidate
        if delta < epsilon:
            break
    final_scores = scores(value)
    for name, row in table.items():
        row["q"] = final_scores[name]
        row["resolved_probability"] = 1 - row["pending_probability"]
    return {"recommended": max(final_scores, key=final_scores.get), "actions": table, "value": value,
            "iterations": iteration, "gamma": gamma, "epsilon": epsilon, "delta": delta}


def _pipeline(method, graph, labels, signals, start, goal, escalation="Escalate to incident team"):
    if method not in ALGORITHMS:
        raise ValueError("Unknown search method")
    routes = {name: search(name, graph, start, goal) for name in ALGORITHMS}
    selected = routes[method]
    if not selected["path"]:
        raise ValueError("The selected page is not reachable through the collected links.")
    belief = update_belief(selected["path"], signals)
    return {
        "method": method, "start": start, "goal": goal, "graph": graph, "labels": labels,
        "routes": routes, "belief": belief,
        "decision": recommend(belief["posterior"], escalation=escalation),
    }


def analyze(method="astar", scenario="complete"):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown scenario")
    result = _pipeline(method, GRAPH, LABELS, SCENARIOS[scenario]["signals"], "report", "decision")
    return {**result, "source": "synthetic", "scenario": scenario}


SITE_LIKELIHOODS = {
    "success": (.45, .83),
    "redirect": (.15, .12),
    "error": (.40, .05),
}
MAX_SITE_PAGES = 6


def _observation(status):
    if 200 <= status < 300:
        return "success"
    if 300 <= status < 400:
        return "redirect"
    if 400 <= status < 600:
        return "error"
    return None


def analyze_website(snapshot, method="astar", destination=None):
    validate_snapshot(snapshot)
    if snapshot.source != "observed" or snapshot.mode != "web":
        raise ValueError("Use an observed website snapshot.")
    by_url = {row.key: row.fields for row in snapshot.records if row.category == "page"}
    if snapshot.scope not in by_url:
        raise ValueError("The starting page did not return an HTTP response.")
    if len(by_url) > MAX_SITE_PAGES:
        raise ValueError("Collect a small snapshot from the DarkPhish tab.")

    urls = [snapshot.scope, *sorted(by_url.keys() - {snapshot.scope})]
    node_for = {url: f"page-{i}" for i, url in enumerate(urls)}
    start = node_for[snapshot.scope]
    graph = {key: [] for key in node_for.values()}
    labels = {key: urlsplit(url).path or "/" for url, key in node_for.items()}
    signals = {}
    pages = []
    for url, key in node_for.items():
        status = by_url[url].get("status")
        pages.append({"id": key, "url": url, "status": status})
        observation = _observation(status) if type(status) is int else None
        if observation:
            signals[key] = (f"{labels[key]} · HTTP {status}", *SITE_LIKELIHOODS[observation])
    for row in snapshot.records:
        if row.category != "link":
            continue
        source, separator, target = row.key.partition(" → ")
        if not separator or source not in node_for or target not in node_for or source == target:
            continue
        status = by_url[target].get("status")
        cost = 1 if type(status) is int and 200 <= status < 300 else 2
        graph[node_for[source]].append((node_for[target], cost))

    reachable = [start]
    seen = {start}
    for node in reachable:
        for target, _ in graph[node]:
            if target not in seen:
                seen.add(target)
                reachable.append(target)
    if destination is not None and destination not in seen:
        raise ValueError("Choose a page linked from the starting URL.")
    goal = destination or next((node for node in reversed(tuple(reachable)) if node != start), start)
    result = _pipeline(method, graph, labels, signals, start, goal, "Escalate for site review")
    return {**result, "source": "observed", "url": snapshot.scope, "pages": pages,
            "reachable": list(reachable), "partial": snapshot.partial}


def print_summary(method="astar", scenario="complete"):
    result = analyze(method, scenario)
    print("DarkPhish in Dropsy | synthetic phishing-report triage")
    print(f"{'Method':6} {'Cost':>4} {'Hops':>4} {'Expanded':>8}   Route")
    for name, route in result["routes"].items():
        print(f"{name:6} {route['cost']:>4} {len(route['path'])-1:>4} {len(route['trace']):>8}   "
              + " > ".join(route["path"]))
    print(f"\nSelected: {method} | Scenario: {scenario}")
    print(f"Prior: {result['belief']['initial']:.2%}")
    for step in result["belief"]["steps"]:
        print(f"{step['posterior']:.2%}: {step['signal']}")
    decision = result["decision"]
    for action, row in decision["actions"].items():
        print(f"{row['q']:+.3f}  {action}")
    print(f"Recommendation: {decision['recommended']} | Bellman iterations: {decision['iterations']}")



def main():
    parser = argparse.ArgumentParser(description="Reproduce the offline DarkPhish course benchmark")
    parser.add_argument("--algorithm", choices=ALGORITHMS, default="astar")
    parser.add_argument("--scenario", choices=SCENARIOS, default="complete")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.json:
        print(json.dumps(analyze(args.algorithm, args.scenario), indent=2))
    else:
        print_summary(args.algorithm, args.scenario)


if __name__ == "__main__":
    main()
