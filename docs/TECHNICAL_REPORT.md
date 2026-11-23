# 📑 Technical Report: DROPSY
## Autonomous AI OSINT Threat Intelligence & Threat Actor De-Anonymization System
**Project:** Dropsy Autonomous OSINT Platform  
**Project Domain:** Artificial Intelligence in Open-Source Intelligence (OSINT) & Cyber Threat Profiling  

---

## 1. Introduction & Real-World Problem Statement
In contemporary cybersecurity, digital forensics, and anti-fraud operations, threat actors routinely shield their true identities behind layers of obfuscation: bulletproof hosting providers, privacy-shielded WHOIS records, CoinJoin cryptocurrency mixers, and pseudonymous developer handles across underground forums and GitHub.

### The Challenge of Manual OSINT Investigations:
1. **Cognitive Overload & Fragmented Data:** An analyst must manually cross-reference dozens of disparate intelligence sources: Certificate Transparency logs (crt.sh), historical passive DNS (pDNS), leaked password breach databases, and public code commit histories.
2. **False Attribution & Homonyms:** Overlapping nicknames, shared public VPN exit nodes, and coincidences frequently lead human investigators down false rabbit holes.
3. **Operational Security (OpSec) Risks:** Reckless active probing (such as direct aggressive port scanning via Shodan or nmap) alerts the adversary, causing them to wipe servers, rotate keys, and abandon infrastructure before attribution is established.

### Project Objectives:
To engineer an autonomous, explainable AI agent (**DROPSY**) capable of:
1. Discovering the optimal verification pivot path from an anonymous seed indicator (e.g. phishing domain, crypto wallet) to the threat actor persona using **Informed Graph Search ($A^*$)**.
2. Disentangling true identity matches from coincidence artifacts using **Bayesian Evidence Fusion**.
3. Formulating an optimal, OpSec-conscious autonomous investigation plan via a **Markov Decision Process (MDP)** solved with **Bellman Value Iteration**.

---

## 2. Mathematical Modeling & Algorithmic Formulation

### 2.1 Pillar 1: Informed Graph Search ($A^*$) on Entity Resolution Graphs
The intelligence space is modeled as a weighted graph $G = (V, E)$, where vertices $v \in V$ represent discovered digital entities (domains, IP addresses, SSL certificates, emails, developer handles, crypto wallets, and real persons), and edges $e = (u, v) \in E$ represent verified pivot relationships.

#### Link Obfuscation Cost $c(u, v)$:
$$c(u, v) = \text{Verification Friction}(u, v)$$
* Unmasked Certificate Transparency SAN link: $c = 2.0$
* Bulletproof hosting IP resolution: $c = 3.0$
* Cryptographic PGP signature link: $c = 1.5$ (lowest friction / highest reliability)
* Obfuscated reverse proxy / mixer hop: $c = 3.5$

#### Admissible & Consistent Heuristic $h(n)$:
To guide the search toward the target persona $S_{\text{target}}$:
$$h(n) = \max\left(0, \text{Tier}(S_{\text{target}}) - \text{Tier}(n)\right) \times c_{\min}$$
where $c_{\min} = 1.5$ is the global lower bound on any relationship verification cost.

#### Proof of Heuristic Admissibility and Consistency:
* **Admissibility ($h(n) \le h^*(n)$):** Any valid pivot from tier $i$ (Seed) to tier $j$ (Real Persona) requires at least $|j - i|$ relationship hops. Since no edge in the OSINT knowledge graph has cost $< c_{\min} = 1.5$, the true shortest path distance $h^*(n) \ge \Delta \text{Tier} \times 1.5$. Thus, $h(n)$ never overestimates the true remaining cost, guaranteeing that $A^*$ returns the optimal attribution path.
* **Consistency:** For any transition $(n, n')$:
  $$h(n) \le c(n, n') + h(n')$$
  The triangle inequality holds strictly because $c(n, n') \ge 1.5 \cdot (\text{Tier}(n') - \text{Tier}(n))$.

---

### 2.2 Pillar 2: Probabilistic Reasoning (Bayesian Identity Attribution)
Let $H \in \{1, 0\}$ denote the hypothesis that an inspected persona is indeed the genuine threat actor operator ($H=1$) versus an innocent namesake or coincidence ($H=0$).

Let $E \in \{\text{PGP\_KEY\_MATCH}, \text{BREACH\_PASSWORD\_HASH}, \text{TIMEZONE\_UTC+3}, \text{COMMIT\_METADATA}\}$ denote observable OSINT evidence artifacts.

#### Evidence Likelihood Model:
* **Sensitivity (True Positive Rate):** $\alpha = P(E \mid H = 1)$
  * PGP Key Match: $\alpha = 0.99$ (Extremely strong cryptographic binding)
  * Breach Password Hash Match: $\alpha = 0.94$ (Reused credentials from credential dumps)
  * Timezone Alignment: $\alpha = 0.85$ (Active commit/forum hours match working day)
* **Coincidence Rate (False Positive Rate):** $\beta = P(E \mid H = 0)$
  * PGP Key Match: $\beta = 0.001$ (Virtually zero chance of identical key by accident)
  * Breach Password Hash Match: $\beta = 0.020$ (Small chance of common password reuse)
  * Timezone Alignment: $\beta = 0.150$ (Many global developers share UTC+3)

#### Recursive Bayesian Update:
$$P(H = 1 \mid E_{1:k}) = \frac{P(E_k \mid H = 1) \cdot P(H = 1 \mid E_{1:k-1})}{P(E_k \mid E_{1:k-1})}$$
where:
$$P(E_k \mid E_{1:k-1}) = \alpha \cdot P_{k-1}(H) + \beta \cdot (1 - P_{k-1}(H))$$
This allows DROPSY to aggregate multiple weak and strong signals into a mathematically calibrated attribution confidence score.

---

### 2.3 Pillar 3: Sequential Decision Making (Bellman MDP Recon Planner)
To optimize the investigation sequence without tipping off the target, the investigation process is formulated as a finite Markov Decision Process:
$$\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma \rangle$$

#### State Space $\mathcal{S}$:
* $s_0$: `S0_INITIAL_SEED` — Raw anonymous indicator.
* $s_1$: `S1_INFRA_UNVEILED` — Hosting, SSL SANs, and IP infrastructure mapped.
* $s_2$: `S2_PERSONA_ISOLATED` — Developer email and GitHub code repos linked.
* $s_3$: `S3_IDENTITY_CONFIRMED` — High-confidence attribution confirmed via Bayes.
* $s_4$: `S4_DOSSIER_COMPLETE` — Forensic dossier assembled for law enforcement.

#### Action Space $\mathcal{A}$:
* $a_0$: `A0_PASSIVE_RECON` — Query public Certificate Transparency logs (crt.sh) and DNS TXT/MX records ($0 OpSec cost).
* $a_1$: `A1_BREACH_QUERY` — Query historical de-hashed breach databases (safe, high identification gain).
* $a_2$: `A2_SOCIAL_CORRELATE` — Crawl public GitHub commit metadata and social handles.
* $a_3$: `A3_ACTIVE_BANNER_GRAB` — Direct port probe / Shodan banner grab (high OpSec risk of alerting adversary).

#### Reward Function $\mathcal{R}(s, a)$:
* Passive recon at initial stage: $+30.0$ (Safe, stealthy progress)
* Active probing at initial stage: $-40.0$ (Severe OpSec burn penalty!)
* Breach correlation when email is discovered: $+45.0$
* Social correlation when persona is isolated: $+50.0$
* Final intelligence dossier completion: $+80.0$

#### Bellman Optimality Equation:
$$V^*(s) = \max_{a \in \mathcal{A}} \left[ \mathcal{R}(s, a) + \gamma \sum_{s' \in \mathcal{S}} \mathcal{P}(s' \mid s, a) V^*(s') \right]$$
with discount factor $\gamma = 0.90$. Value Iteration runs until $\|V_{k+1} - V_k\|_\infty < 10^{-3}$.

---

## 3. Experimental Evaluation & Results

### 3.1 Search Algorithm Benchmark ($A^*$ vs Dijkstra)
| Metric | Uninformed Dijkstra | Admissible $A^*$ Search | Efficiency Gain |
|---|:---:|:---:|:---:|
| **Optimal Path Discovered** | Yes | Yes | Identical Path |
| **Path Traversal Cost** | $10.50$ | $10.50$ | Mathematically Optimal |
| **Entities Expanded** | $8$ entities | $7$ entities | **$12.5\%$ reduction in state expansion** |
| **Execution Latency** | $0.18$ ms | $0.14$ ms | **$22.2\%$ speedup** |

### 3.2 Sequential Bayesian Attribution Progression
Starting from a base prior confidence of $P(H) = 10.0\%$:
1. **Evidence 1 (PGP GPG Key Match):** Posterior surges to **$99.1\%$** ($TPR=0.99, FPR=0.001$).
2. **Evidence 2 (Breach Password Hash):** Posterior reaches **$99.9\%$** ($TPR=0.94, FPR=0.02$).
3. **Evidence 3 (Timezone UTC+3 Cadence):** Posterior approaches **$\approx 100.0\%$**.

### 3.3 Bellman MDP Convergence & Optimal Policy
* Convergence achieved in **$11$ iterations** ($\epsilon < 0.001$).
* **Extracted Optimal Policy $\pi^*(s)$**:
  * $\pi^*(S_0) = \text{A0\_PASSIVE\_RECON}$ ($Q = 180.6$ beats active probe $Q = 109.2$).
  * $\pi^*(S_1) = \text{A1\_BREACH\_QUERY}$ ($Q = 165.0$).
  * $\pi^*(S_2) = \text{A2\_SOCIAL\_CORRELATE}$ ($Q = 129.9$).
  * $\pi^*(S_3) = \text{A0\_PASSIVE\_RECON}$ ($Q = 81.5$).

---

## 4. Ethical, Privacy & Legal Considerations
DROPSY operates exclusively on **publicly verifiable open-source intelligence (OSINT)** and public cryptographic ledgers. No private communications are intercepted, and no unauthorized computer intrusions are performed. All generated commands rely on standard passive reconnaissance protocols (DNS, Certificate Transparency, and public API registries) compliant with international cyber investigation standards.
