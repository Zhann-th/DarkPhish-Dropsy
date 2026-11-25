# AI Usage Declaration

Project: DarkPhish · AI Fundamentals  
Student: Zhanassyl Syrlibayev  
Date: 2026-11-24  

## AI Tool and Role (Minimal Assistance)

- **Assistance Scope:** Minimal editorial assistance for formatting documentation syntax, checking English grammar and spelling in reports, and synthetic text-to-speech voice generation for the narration audio in the demonstration video.
- **Independent Algorithm Implementation:** All core algorithms — Graph Search (BFS, DFS, UCS, A* with admissible heuristic), Bayesian sequential probability updating, and Markov Decision Process (Bellman value iteration) — were independently designed, mathematically derived, and implemented in Python by the student without generative code generation.
- **Deterministic Runtime:** The application and all decision-making pipelines run deterministically and do not require any generative AI models or external AI APIs at runtime.

## Student Verification

- **Student Name:** Zhanassyl Syrlibayev
- **Sections Reviewed and Verified:** All algorithm modules (`darkphish_course.py`, `mdp_engine.py`, `bayes_engine.py`, `search_engine.py`), API routes, test cases, and documentation.
- **Commands Personally Run:**
  - `python3 -m unittest discover -s tests` (All 49 unit tests passed)
  - `python3 -m dropsy.core.darkphish_course` (CLI verification of search, Bayes, and MDP)
  - `python3 main.py --server` (Local web interface verification)
- **Date:** November 24, 2026
