# Live defense

## Problem and objectives · 2 minutes

“When an analyst receives a phishing report, some observations may be expensive or unavailable. A quick decision can miss a genuine incident. Escalating benign mail also consumes time. Our objective is to choose a route through the available evidence and recommend a response that makes those trade-offs explicit. DarkPhish runs on a synthetic fixture so we can isolate and explain each decision.”

Explain that one pipeline links the chosen route, the probability, and the action. Point out the two outcomes that cause the greatest operational cost: missed incidents and unnecessary escalation.

## Live demonstration · 3–5 minutes

1. Start Dropsy with `python3 main.py --server` and open `http://127.0.0.1:8000/darkphish`. Select **A*** and **All observations available**. Run triage.
2. Compare the four rows. A* and UCS both find cost 6. BFS finds a shorter route in hops but a higher-cost route. Expand the trace and point to g, h and f.
3. Read 10% → 28.57% → 80.95% and show the final Q values. The model recommends escalation.
4. Select **Analyst finding unavailable**, then run again. The route stays the same, the probability falls to 28.57%, and the recommendation becomes manual review.
5. Restore all observations and choose BFS. The route goes through the allowlist lookup. The model reaches 6.60% and gives low priority. Discuss why a low-hop route can miss informative observations.

6. Select **Public website URL** and enter a public URL. After **Collect website**, select a destination and run the same pipeline. Show the HTTP observations and explain that the likelihoods are illustrative. If only the initial page is available, show the resulting zero-hop route and use the synthetic trace for comparison.

## Three AI topics · 2 minutes

- **Search:** BFS minimizes hops. DFS follows a fixed depth-first order. UCS uses g. A* adds h, a lower bound from remaining hops and minimum edge cost.
- **Bayes:** The likelihoods determine how far the prior moves. Sequential updates assume conditional independence in this model.
- **MDP:** The posterior weights rewards for phishing and benign states of the email. Bellman value iteration also accounts for the chance a review leaves the case pending.

## Individual Q&A · Up to 3 minutes

| Question | Answer |
|---|---|
| Why are four search methods only one topic? | All four solve the graph-search subproblem. Bayesian inference and MDP supply the other two course topics. |
| Why does BFS cost 10? | Its selected path uses two edges with costs 6 and 4. The three-edge alternative costs 6 in total. |
| Why is A*'s heuristic admissible? | A path needs at least the minimum number of remaining hops. Each edge costs at least the global minimum edge cost. |
| Did A* run faster than UCS? | We counted 6 versus 7 expansions on this fixture. We excluded heuristic preprocessing and did not measure runtime. |
| What makes Bayes and MDP connected? | The posterior changes expected rewards, which changes the Bellman action scores. |
| What makes search and Bayes connected? | Bayes processes only observations on the selected path. A different route exposes different observations. |
| What if two observations are correlated? | The assumed likelihood product can overstate confidence. Estimate a joint likelihood or model their dependency. |
| Why does missing evidence change the output? | The absent analyst signal contributes no update. At 28.57%, the expected utility favors manual review. |
| What makes this an MDP? | States, actions, transition probabilities, rewards and a discount determine action values over time. |
| Can you claim detection accuracy? | The toy inputs demonstrate the pipeline. Accuracy needs labeled cases and independent evaluation. |
