# DarkPhish technical report
## Phishing report triage

### Problem and scope

An analyst handling a reported email must decide whether to lower its priority, request a manual review, or escalate it. Choosing which observations to consider matters when analyst time is limited. The project models one report using seven synthetic graph nodes, two evidence scenarios, and a two-state MDP. The DarkPhish tab in Dropsy supports this offline benchmark and a separate mode that collects public website observations.

### Integrated pipeline

The selected search method returns an ordered path. The inference stage takes only the observations attached to nodes on that path. The MDP receives the Bayesian posterior and converts it to an expected immediate reward for each action. The highest converged action value determines the recommendation. Changing the route therefore changes the evidence available to the decision.

### 1. Graph search

Directed edges carry positive costs that stand for review effort. BFS uses a FIFO frontier and minimizes the number of edges. DFS uses a LIFO frontier and its output depends on fixed adjacency order. UCS uses a priority queue ordered by cumulative edge cost. A* orders the queue by `f(n) = g(n) + h(n)`. In the demo, `h(n)` equals the minimum remaining hop count from reverse BFS multiplied by the minimum edge cost. Each real remaining edge costs at least that minimum. If an edge leads from `u` to `v`, the hop count of `u` is at most one plus the hop count of `v`. Thus `h(u) ≤ cost(u,v) + h(v)` for goal-reachable successors. The fixture has only goal-reachable nodes.

The table counts each current expansion including the goal, and excludes A* preprocessing. The heuristic is reusable when the graph and goal are fixed. The single search result does not establish a runtime speedup.

| Algorithm | Cost | Hops | Expansions |
|---|---:|---:|---:|
| BFS | 10 | 2 | 6 |
| DFS | 13 | 4 | 5 |
| UCS | 6 | 3 | 7 |
| A* | 6 | 3 | 6 |

### 2. Bayesian inference

Let H mean that the reported email is phishing. Begin at P(H) = 0.10. For each observed signal E, use the previous posterior as the next prior.

`P(H|E) = P(E|H) P(H) / [P(E|H) P(H) + P(E|¬H) (1 − P(H))]`

| Observation | P(E\|H) | P(E\|¬H) | Posterior along A* |
|---|---:|---:|---:|
| Header authentication signal failed | 0.72 | 0.20 | 28.57% |
| Analyst found a synthetic credential prompt | 0.85 | 0.08 | 80.95% |

The model assumes conditional independence given H and its complement. The likelihoods are illustrative inputs, so these posteriors describe the model. Missing evidence leaves the current probability unchanged.

### 3. Bellman value iteration

The two states are pending and resolved. The resolved state is absorbing and has value zero. Pending supports closing, manual review and escalation. The reward table uses illustrative utility units.

| Action | Reward if H | Reward if ¬H | P(still pending) |
|---|---:|---:|---:|
| Close as low priority | −12 | +2 | 0.00 |
| Request manual review | −1 | −1 | 0.25 |
| Escalate to incident team | +6 | −6 | 0.00 |

For posterior p, compute `E[R] = pR(H) + (1−p)R(¬H)`. Starting with zero, repeatedly set `V(pending) = max_a(E[R] + 0.9 P(pending|a) V(pending))` until the absolute update is below `1e-8`. This model holds p fixed within the calculation. A fresh review observation is handled by a new run. At 80.95%, the action scores for close, review and escalate are −9.333, −0.164 and +3.714.

### Evaluation

| Run | Posterior | Decision |
|---|---:|---|
| A*, all observations | 80.95% | Escalate |
| A*, analyst finding unavailable | 28.57% | Request manual review |
| BFS, all observations | 6.60% | Close as low priority |

The BFS outcome illustrates what can happen when a low-hop route misses relevant evidence. Further work could compare alternate routes, estimate likelihoods from labeled reports, calibrate probabilities on a held-out set, and test sensitivity to false-positive and false-negative costs. A deployment study should include analyst review and report both types of errors.

Reproduce the benchmark with `python3 -m dropsy.core.darkphish_course`. Reproduce the intervention with `python3 -m dropsy.core.darkphish_course --scenario missing`. The fixture tests check route costs and counts, heuristic consistency, unreachable targets, Bayes arithmetic, absent evidence, policy changes, and the Bellman stopping condition.


### Public website mode in Dropsy

DarkPhish reuses the bounded HTTP collector and requests at most six public pages from the same origin. It uses HTTP GET and recorded HTML links. The UI lets the user choose a reachable destination. A link costs 1 if its target returns 2xx and 2 otherwise. This is a model of review effort. The route becomes the sequence of HTTP observations consumed by Bayes.

| HTTP observation | P(E given review-worthy route) | P(E given routine route) |
|---|---:|---:|
| 2xx | 0.45 | 0.83 |
| 3xx | 0.15 | 0.12 |
| 4xx or 5xx | 0.40 | 0.05 |

Website mode starts at a prior of 0.10. It uses the same Bellman solver with website-review action labels. The likelihoods, independence assumption, cost rule and MDP rewards are illustrative and have no calibration for judging a real site. The collector stops at redirects and does not execute JavaScript. A single observed page supports a zero-hop route. A missing starting response prevents the pipeline from running. A test fixture exercises collection, direction of edges, posterior and action scores without relying on a third-party server.
