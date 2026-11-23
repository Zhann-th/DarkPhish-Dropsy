# Demo video · 2 minutes 44 seconds

The video presents verified CLI outputs and a public website mode replay with test HTTP responses, captions and synthetic English narration. For live defense, use the browser controls to reproduce the same runs.

| Time | What to show |
|---|---|
| 00:00–00:20 | Problem, offline synthetic fixture and the connected pipeline. |
| 00:20–00:49 | Run `python3 -m dropsy.core.darkphish_course`. Compare BFS, DFS, UCS and A*. Explain the distinct measures of cost, hops and expansions. |
| 00:49–01:12 | Read the two sequential Bayes updates. Explain why the chosen evidence matters. |
| 01:12–01:36 | Show the three Q values. The highest value selects escalation in the default run. |
| 01:36–02:04 | Run `python3 -m dropsy.core.darkphish_course --scenario missing`. Show the switch to manual review. |
| 02:04–02:24 | Run `python3 -m dropsy.core.darkphish_course --algorithm bfs`. Explain how changing the route changes the recommendation and summarize the limits. |
| 02:24–02:44 | Switch to Public website URL. Show a saved replay with HTTP 200 and 404, its route cost and the review recommendation. Live collection uses the entered URL. |
