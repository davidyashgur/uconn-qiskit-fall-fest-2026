# Instant Insanity with constrained QAOA

Our submission for the qBraid challenge at **Qiskit Fall Fest Connecticut 2026**: stack four colored cubes so every side of the tower shows every color once, using a quantum algorithm run on AWS SV1 through qBraid.

## Team

Anthony Secora | Kajal Singh | Tyler Hubeny | David Yashgur

## Level reached

**Core**, run on SV1: the full four-cube puzzle (front/back and left/right) on 24 qubits, **71.8% of shots a correct tower** at p = 16.
**Bonus**, partly: the same method generalized to N cubes and N colors, tuned and simulated exactly for N = 5 and 6.

## Approach

**Encoding.** Each cube gets 6 qubits in two blocks of 3: one block says which opposite-face pair faces front/back, the other which pair faces left/right (one-hot, so exactly one qubit per block is 1). Four cubes give 8 blocks, 24 qubits.

**Cost.** A Hamiltonian made of Z and ZZ terms scores each choice: a penalty when a color does not appear exactly twice on front/back or on left/right, and a penalty when one pair is used for both axes. It is 0 only for a solved tower.

**Algorithm: constrained QAOA.** Every block starts in a W state (an equal mix of its three one-hot options) and is mixed with XY (`XXPlusYYGate`) mixers, which move the 1 inside a block but never create or destroy one. So the circuit only explores the 3⁸ = 6,561 valid choices instead of 2²⁴ ≈ 16.8 million bit strings, and the "one pair per axis" rule never needs a penalty.

**Tuning.** Because the circuit never leaves the 6,561 valid choices, we simulate it exactly on those choices alone (a 3×3 mixer matrix per block). That makes tuning fast: a grid search at p = 1, then COBYLA adding one layer at a time up to p = 16. The tuned circuits for p = 8 and p = 16 then run on SV1.

## Classical checks

All in `solution.ipynb`, Section 7.1 onward:

- The Hamiltonian equals the classical `cost` on all 6,561 valid choices (largest gap 0).
- The lowest-energy choices (energy 0) are **exactly** the 2 choices an independent tower checker (`solves(tower_from(...))`) accepts: the tower and its quarter turn. Everything else has energy ≥ 2.
- Our fast simulator matches Qiskit Aer running the real 24-qubit circuit to ~1e-17, and the real circuit puts no probability outside the valid choices.
- The bit string decoder is tested on the known answer (minding Qiskit's bit order) before use.
- Every shot is decoded and run through the tower checker; only towers that pass count as correct.
- For the bonus, the same checks run for each N, and our general Hamiltonian reproduces the starter's `build_hamiltonian` exactly on four cubes.

## Results

| Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates (after transpiling) | Depth | Shots | P(correct tower) | Random-guess baseline | qBraid job ID |
|---|---|---|---|---|---|---|---|---|---|
| 4, front/back only (warm-up) | one-hot x, W + XY mixer, p = 2 | `aws:aws:sim:sv1` | 12 | — | — | 1000 | 24.5% good front/back picks (exact 28.4%) | 4 / 2¹² ≈ 0.1% | `aws:aws:sim:sv1-3ccf-qjob-6ad3b03e38127b44c71ba087` |
| 4 (core) | one-hot x and y, W + XY mixer, p = 8 | `aws:aws:sim:sv1` | 24 | 2,400 | 871 | 1000 | 32.4% (exact 31.8%) | 2 / 2²⁴ ≈ 1.2 × 10⁻⁷ (random valid choice: 2 / 6,561 ≈ 0.03%) | `aws:aws:sim:sv1-3ccf-qjob-6ad3b07638127b44c71ba0a3` |
| **4 (core)** | one-hot x and y, W + XY mixer, p = 16 | `aws:aws:sim:sv1` | 24 | 4,736 | 1,719 | 1000 | **71.8%** (exact 73.3%) | 2 / 2²⁴ ≈ 1.2 × 10⁻⁷ (random valid choice: 2 / 6,561 ≈ 0.03%) | `aws:aws:sim:sv1-3ccf-qjob-6ad3b0b638127b44c71ba0bd` |
| 5 (bonus) | same, p = 6 | exact subspace simulation | 30 | 2,324 | 713 | — | 6.1% (exact) | 2 / 2³⁰ ≈ 1.9 × 10⁻⁹ (random valid: 0.0034%) | — |
| 6 (bonus) | same, p = 6 | exact subspace simulation | 36 | 2,760 | 677 | — | 2.9% (exact) | 2 / 2³⁶ ≈ 2.9 × 10⁻¹¹ (random valid: 0.0004%) | — |

Two-qubit gates and depth are counted after `transpile(qc, basis_gates=["rz", "sx", "x", "cx"])`. Bonus puzzles use `make_puzzle` with the starter's seeds (N = 5: seed 16, N = 6: seed 86), each checked with `count_answers` to have exactly one tower.

How success grows with QAOA rounds on the core puzzle (exact, from the subspace simulator; p ≤ 16 is in the notebook, p = 20 to 25 from a separate run of the same tuning):

| p | 1 | 2 | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 20 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P(correct tower) | 0.7% | 2.4% | 9.8% | 22.6% | 31.8% | 41.9% | 50.6% | 63.4% | 73.3% | 80% | 86% | 89% |
| CX gates | 356 | 648 | 1,232 | 1,816 | 2,400 | | 3,568 | | 4,736 | | ≈ 5,900 | ≈ 7,400 |

Each round costs about 292 CX. Success climbs 3 to 5 points per round up to p ≈ 20, then levels off near 87 to 89%, with less than one point per extra round. That plateau may come from near-miss towers (energy 2) or from COBYLA struggling with 40 to 50 angles; we did not separate the two.

**What this does and does not show.** At p = 16, constrained QAOA puts about 72% of its shots on the single correct tower, about 2,400× a random valid choice. It is **not** faster than classical computing: brute force checks all 331,776 towers in about 0.1 s, and our angle tuning itself simulates the 6,561 valid choices classically. Depth is free on a noise-free simulator but not on real hardware: a 4,700-CX circuit would be dominated by noise on today's QPUs. The SV1 core results sit within about one standard deviation of the exact values (1,000 shots give about ±1.5%); the warm-up rerun came in 2.8 standard deviations low (24.5% vs 28.4%), and an earlier run of the same circuit gave 28.3%. N = 6 needs 36 qubits, above SV1's 34-qubit limit, so with this encoding N = 5 is the largest size SV1 could run.

**Next step.** A cube has only 6 valid choices, which fit in 3 qubits instead of 6. That halves the qubit count (N = 8 would fit in 24 qubits) at the cost of three-qubit Z terms in the Hamiltonian.

### All qBraid jobs

The jobs behind the table are the ones in the saved notebook. Earlier runs of the same notebook, kept for completeness:

- `aws:aws:sim:sv1-3ccf-qjob-6ad3a87238127b44c71b9f81`: warm-up, 28.3% good picks
- `aws:aws:sim:sv1-3ccf-qjob-6ad3a89a38127b44c71b9f89`: core p = 8, 28.8% correct towers
- one more warm-up job from a run that stopped on a bug in our p = 16 cell

## How to run

Open `solution.ipynb` in qBraid Lab and run all cells from the top. The first cell installs anything missing. Sections 1 to 6 are the challenge's starter notebook (with our `submit_job`); **Sections 7 and 8 are our solution**. A full run takes about 5 minutes and submits three SV1 jobs (warm-up, p = 8, p = 16); the N = 6 bonus tuning takes about 3 minutes.

Locally:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
qbraid configure          # needs a qBraid API key; never put it in the notebook
jupyter lab solution.ipynb
```

Random seeds are fixed (`SEED = 7`). SV1 shot results vary slightly from run to run.

## AI use

We used **Claude Code** (Anthropic's AI coding agent) throughout:

- It read the challenge files and proposed the approach (extending the warm-up's constrained QAOA to all 24 qubits).
- It wrote the code in Sections 7 and 8 of `solution.ipynb`: the classical checks, the fast subspace simulator, the angle tuning, the decoder and the bonus generalization. It also set up this repository and drafted this README.
- We wrote `submit_job` ourselves; the agent reviewed it and caught two typos before we spent credits.

How we checked its output: every piece of generated code is backed by a classical check in the notebook. The Hamiltonian is compared with brute-force cost on every valid choice, the fast simulator is compared with Qiskit Aer on the real 24-qubit circuit, the decoder is tested on the known answer, and every reported tower is verified with the starter's own `solves` checker.

## Repository layout

```
├── README.md          this file
├── slides.pdf         presentation
├── solution.ipynb     main notebook, saved with outputs
├── requirements.txt   Python packages (same as the challenge)
└── resources/         helpers.py and __init__.py from the challenge starter
```
