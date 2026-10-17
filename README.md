# Instant Insanity with QAOA — UConn Qiskit Fall Fest 2026

Our submission for the qBraid challenge at Qiskit Fall Fest Connecticut 2026: solve the Instant Insanity cube puzzle with a quantum algorithm, run on AWS SV1 through qBraid.

## Team

_TODO: names_

## Level reached

_TODO: warm-up / core / bonus_

## Approach

_TODO: encoding and algorithm in a few sentences._

## How to run

Open `solution.ipynb` in qBraid Lab and run all cells from the top. The first cell installs anything missing.

Locally:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab solution.ipynb
```

To submit to SV1 from your own machine, run `qbraid configure` or set `QBRAID_API_KEY` in your shell first.

## Results

| Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates (after transpiling) | Depth | Shots | P(correct tower) | Random-guess baseline | qBraid job ID |
|---|---|---|---|---|---|---|---|---|---|

## qBraid job IDs

_TODO_

## AI use

_TODO: which tools, for which parts, and how we checked their output._

## Repository layout

```
├── README.md          this file
├── solution.ipynb     main notebook, saved with outputs
├── requirements.txt   Python packages
└── resources/         helpers.py from the challenge starter
```
