"""
Dropsy OSINT: Graph Search Engine for Threat Actor Attribution & Pivot Discovery.
Implements A* Search with provably admissible heuristic, Dijkstra, and Step-by-Step tracing.
"""

import heapq
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from .entity_graph import OsintKnowledgeGraph, OsintEntity


@dataclass
class SearchResult:
    algorithm: str
    start_entity: str
    target_entity: str
    path_found: bool
    optimal_path: List[str]
    path_names: List[str]
    total_cost: float
    nodes_expanded: int
    execution_trace: List[dict]
    critical_pivots: List[str]

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "start_entity": self.start_entity,
            "target_entity": self.target_entity,
            "path_found": self.path_found,
            "optimal_path": self.optimal_path,
            "path_names": self.path_names,
            "total_cost": round(self.total_cost, 2),
            "nodes_expanded": self.nodes_expanded,
            "execution_trace": self.execution_trace,
            "critical_pivots": self.critical_pivots,
        }


class OsintPathSearchEngine:
    """
    Searches for the lowest-friction verification path from an initial seed artifact
    to the deanonymized threat actor profile.
    """

    MIN_PIVOT_COST = 1.5  # Minimum theoretical obfuscation cost across any OSINT relationship

    def __init__(self, graph: OsintKnowledgeGraph):
        self.graph = graph

    def admissible_heuristic(self, current_id: str, target_id: str) -> float:
        """
        Admissible & Consistent Heuristic h(n):
        h(n) = max(0, TargetTier - CurrentTier) * MIN_PIVOT_COST
        Never overestimates remaining cost to de-anonymize the target actor.
        """
        curr = self.graph.entities.get(current_id)
        tgt = self.graph.entities.get(target_id)
        if not curr or not tgt:
            return 0.0

        tier_diff = tgt.tier - curr.tier
        if tier_diff <= 0:
            return 0.0
        return float(tier_diff * self.MIN_PIVOT_COST)

    def a_star_search(self, start_id: str, target_id: str) -> SearchResult:
        """Executes A* search to uncover optimal threat actor attribution path."""
        if start_id not in self.graph.entities or target_id not in self.graph.entities:
            return SearchResult(
                algorithm="A*", start_entity=start_id, target_entity=target_id,
                path_found=False, optimal_path=[], path_names=[], total_cost=0.0,
                nodes_expanded=0, execution_trace=[], critical_pivots=[]
            )

        counter = 0
        h_start = self.admissible_heuristic(start_id, target_id)
        open_heap: List[Tuple[float, int, str, List[str], float]] = [
            (h_start, counter, start_id, [start_id], 0.0)
        ]
        g_scores: Dict[str, float] = {start_id: 0.0}
        closed_set: Set[str] = set()
        trace_log = []
        step = 0

        while open_heap:
            f_curr, _, curr_id, path, g_curr = heapq.heappop(open_heap)
            step += 1

            if curr_id in closed_set and g_curr > g_scores.get(curr_id, float("inf")):
                continue

            closed_set.add(curr_id)
            current_open = [item[2] for item in open_heap]

            trace_log.append({
                "step": step,
                "current_entity": curr_id,
                "current_name": self.graph.entities[curr_id].name,
                "g_score": round(g_curr, 2),
                "h_score": round(self.admissible_heuristic(curr_id, target_id), 2),
                "f_score": round(f_curr, 2),
                "open_set": list(set(current_open)),
                "closed_set": list(closed_set),
                "action": f"Inspected '{self.graph.entities[curr_id].name}' (f={f_curr:.1f})"
            })

            if curr_id == target_id:
                path_names = [self.graph.entities[n].name for n in path]
                critical_pivots = path[1:-1]
                return SearchResult(
                    algorithm="A*",
                    start_entity=start_id,
                    target_entity=target_id,
                    path_found=True,
                    optimal_path=path,
                    path_names=path_names,
                    total_cost=g_curr,
                    nodes_expanded=len(closed_set),
                    execution_trace=trace_log,
                    critical_pivots=critical_pivots
                )

            for nbr_id, edge_cost in self.graph.get_neighbors(curr_id):
                if nbr_id in closed_set:
                    continue
                tentative_g = g_curr + edge_cost
                if tentative_g < g_scores.get(nbr_id, float("inf")):
                    g_scores[nbr_id] = tentative_g
                    h_val = self.admissible_heuristic(nbr_id, target_id)
                    f_val = tentative_g + h_val
                    counter += 1
                    heapq.heappush(open_heap, (f_val, counter, nbr_id, path + [nbr_id], tentative_g))

        return SearchResult(
            algorithm="A*", start_entity=start_id, target_entity=target_id,
            path_found=False, optimal_path=[], path_names=[], total_cost=float("inf"),
            nodes_expanded=len(closed_set), execution_trace=trace_log, critical_pivots=[]
        )

    def dijkstra_search(self, start_id: str, target_id: str) -> SearchResult:
        """Standard uninformed Dijkstra for comparative benchmark."""
        counter = 0
        open_heap: List[Tuple[float, int, str, List[str]]] = [(0.0, counter, start_id, [start_id])]
        g_scores: Dict[str, float] = {start_id: 0.0}
        closed_set: Set[str] = set()
        trace_log = []
        step = 0

        while open_heap:
            g_curr, _, curr_id, path = heapq.heappop(open_heap)
            step += 1
            if curr_id in closed_set:
                continue
            closed_set.add(curr_id)

            if curr_id == target_id:
                return SearchResult(
                    algorithm="Dijkstra", start_entity=start_id, target_entity=target_id,
                    path_found=True, optimal_path=path,
                    path_names=[self.graph.entities[n].name for n in path],
                    total_cost=g_curr, nodes_expanded=len(closed_set),
                    execution_trace=trace_log, critical_pivots=path[1:-1]
                )

            for nbr_id, edge_cost in self.graph.get_neighbors(curr_id):
                if nbr_id in closed_set:
                    continue
                tentative_g = g_curr + edge_cost
                if tentative_g < g_scores.get(nbr_id, float("inf")):
                    g_scores[nbr_id] = tentative_g
                    counter += 1
                    heapq.heappush(open_heap, (tentative_g, counter, nbr_id, path + [nbr_id]))

        return SearchResult(
            algorithm="Dijkstra", start_entity=start_id, target_entity=target_id,
            path_found=False, optimal_path=[], path_names=[], total_cost=float("inf"),
            nodes_expanded=len(closed_set), execution_trace=trace_log, critical_pivots=[]
        )
