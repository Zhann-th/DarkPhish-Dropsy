# Dropsy 7.5 · DarkPhish — AI Fundamentals Final Project

> **Live Demo:** [https://dropsy-repo.vercel.app/darkphish](https://dropsy-repo.vercel.app/darkphish)  
> **Student:** Zhanassyl Syrlibayev (`Zhann-th`)  
> **Course:** AI Fundamentals  
> **Submission Type:** Individual  

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Vercel](https://img.shields.io/badge/deployed_on-Vercel-black.svg?logo=vercel)](https://dropsy-repo.vercel.app/darkphish)
[![Tests Passing](https://img.shields.io/badge/tests-49%20passed-brightgreen.svg)]()

---

## Required Deliverables

| Deliverable | Location / Link |
|---|---|
| **Live / Local Demo** | [https://dropsy-repo.vercel.app/darkphish](https://dropsy-repo.vercel.app/darkphish) *(or local `http://127.0.0.1:8000/darkphish`)* |
| **GitHub Repository** | [https://github.com/Zhann-th/DarkPhish-Dropsy](https://github.com/Zhann-th/DarkPhish-Dropsy) |
| **5–7 Slide Presentation** | [`docs/darkphish/presentation.pptx`](docs/darkphish/presentation.pptx) (7 slides with diagrams and UI screenshots) |
| **2–3 Minute Demo Video** | [`docs/darkphish/demo.mp4`](docs/darkphish/demo.mp4) (2:30, voiced and synced narration) |
| **Technical Report** | [`docs/darkphish/TECHNICAL_REPORT.md`](docs/darkphish/TECHNICAL_REPORT.md) (Complete mathematical formulas and derivations) |
| **Team Contribution Statement** | [`docs/darkphish/TEAM_CONTRIBUTION.md`](docs/darkphish/TEAM_CONTRIBUTION.md) (Individual submission) |
| **AI Usage Declaration** | [`docs/darkphish/AI_USAGE_DECLARATION.md`](docs/darkphish/AI_USAGE_DECLARATION.md) (Minimal editorial & synthetic TTS voiceover) |
| **Project Defense Guide & Q&A** | [`docs/darkphish/DEFENSE.md`](docs/darkphish/DEFENSE.md) (2m problem, 4m demo, 2m topics, 3m Q&A) |

---

## Three AI Topics Implemented

1. **Graph Search (A\*, UCS, BFS, DFS):**
   - Finds optimal evidence paths on a weighted graph with non-uniform edge costs.
   - **A\*** uses an admissible heuristic $h(n)$ based on remaining minimum hops and global minimum edge cost ($c_{\min} = 1$). Both A\* and UCS find the optimal cost of 6 (via header review and analyst finding).
   - **BFS** minimizes hops (2 hops) but selects a higher-cost route (cost 10) through allowlist lookup.
   - **DFS** follows fixed depth-first order.

2. **Probabilistic Reasoning (Bayesian Sequential Updating):**
   - Updates the posterior probability $P(\text{Phishing} \mid E)$ sequentially across evidence observations collected along the chosen search route:
     $$P(H \mid E) = \frac{P(E \mid H) P(H)}{P(E \mid H) P(H) + P(E \mid \neg H) (1 - P(H))}$$
   - Starting from a prior of $10.0\%$:
     - Failed header raises it to $28.57\%$.
     - Analyst finding raises it to $80.95\%$.
   - Demonstrates how different search routes supply different evidence and alter the final belief.

3. **Sequential Decision Making (Markov Decision Process with Bellman Value Iteration):**
   - Evaluates three triage actions: **Close**, **Review**, and **Escalate**.
   - Solves for state values using Bellman value iteration with discount factor $\gamma = 0.9$:
     $$V(s) = \max_{a} \left[ R(s, a) + \gamma \sum_{s'} P(s' \mid s, a) V(s') \right]$$
   - At $80.95\%$ posterior probability, **Escalate** achieves the highest Q-score ($+3.7.5$), driving the automated triage decision. When evidence is missing, probability drops to $28.57\%$, switching the recommendation to **Manual Review**.

### New in Dropsy 7.5 · DarkPhish Mail & Link Inspector
- Support for parsing real `.eml` emails, raw email text, and URL links with heuristic multi-hop search, Bayesian aggregation, and Bellman triage scoring.
- Added sample emails: [`docs/darkphish/examples/ordinary.eml`](docs/darkphish/examples/ordinary.eml) and [`docs/darkphish/examples/suspicious.eml`](docs/darkphish/examples/suspicious.eml).
- Total unit tests expanded to 49.

---

## How to Run

### Option 1: Live Web Demo (Zero Installation)
Visit the live Vercel deployment:
👉 **[https://dropsy-repo.vercel.app/darkphish](https://dropsy-repo.vercel.app/darkphish)**

### Option 2: Local Web Server
Requires Python 3.11+.

```bash
# 1. Clone repository
git clone https://github.com/Zhann-th/DarkPhish-Dropsy.git
cd DarkPhish-Dropsy

# 2. Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch web platform
python3 main.py --server
```

Open **[http://127.0.0.1:8000/darkphish](http://127.0.0.1:8000/darkphish)** in your browser.

### Option 3: Command-Line Interface (CLI Benchmarks)

Run the deterministic benchmark pipeline without opening a browser:

```bash
# Default run (A* search -> Bayes update to 80.95% -> Escalate action)
python3 -m dropsy.core.darkphish_course

# Missing evidence scenario (Analyst finding unavailable -> Bayes 28.57% -> Manual Review)
python3 -m dropsy.core.darkphish_course --scenario missing

# BFS search algorithm (takes 2-hop route -> Bayes 6.6% -> Low Priority)
python3 -m dropsy.core.darkphish_course --algorithm bfs
```

### Option 4: Run Test Suite

Verify all 49 automated unit tests:

```bash
python3 -m unittest discover -s tests
```
