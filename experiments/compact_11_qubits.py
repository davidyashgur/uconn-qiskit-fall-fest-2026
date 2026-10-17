"""Experiment: the four-cube puzzle on 11 qubits (3 bits per cube, symmetry removed).

Standalone version of our 11-qubit experiment, run from the repo root:
    python experiments/compact_11_qubits.py
It builds the encoding, runs the classical checks, tunes plain-mixer QAOA up to p = 20
with an exact 2,048-state simulator, and samples 1,000 shots of the p = 20 circuit on
the local Aer simulator (not SV1). Saved output: experiments/compact_11_qubits_output.txt
The explanation of each step is in the comments and in the README.
"""
import itertools
import sys
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer import AerSimulator
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from resources.helpers import SEED, diagonal, prepare, strip_marker, tower_from  # noqa: E402

# --- from the starter notebook
COLOURS = "RGBY"
CUBES = [["GR", "BR", "GY"], ["GY", "RB", "BY"], ["BR", "RG", "RY"], ["YR", "RG", "BG"]]
CHOICES = list(itertools.permutations(range(3), 2))   # (front/back pair, left/right pair)


def solves(tower):
    """True when each of the four sides shows four different colours."""
    return all(len({view[side] for view in tower}) == len(tower) for side in range(4))


def circuit_size(qc):
    """CX count and depth after transpiling to rz, sx, x, cx, as GRADING.md asks."""
    measured = qc.copy()
    measured.measure_all()
    t = transpile(measured, basis_gates=["rz", "sx", "x", "cx"], optimization_level=1, seed_transpiler=SEED)
    return t.count_ops().get("cx", 0), t.depth()


def run_on_qbraid(circuit, shots=1000):
    """Local stand-in: same prepare/strip_marker path as the notebook, on Aer instead of SV1."""
    qc = prepare(circuit)
    return strip_marker(AerSimulator(seed_simulator=SEED).run(qc, shots=shots).result().get_counts())


# --- our 11-qubit experiment

# Encoding: cube 1 uses qubits 0-1, cube 2 qubits 2-4, cube 3 qubits 5-7, cube 4 qubits 8-10.
FIRST_CHOICES = [(0, 1), (0, 2), (1, 2)]   # cube 1: front/back pair < left/right pair (breaks the symmetry)
WIDTHS = [2, 3, 3, 3]                       # qubits per cube
OFFSETS = [0, 2, 5, 8]                      # first qubit of each cube
N_COMPACT = sum(WIDTHS)                     # 11
PENALTY = 4                                 # cost per cube with an invalid code


def compact_decode(index):
    """Bitstring as an integer (qubit q = bit q) -> one (front/back, left/right) choice per cube.

    A cube with an invalid code gets None.
    """
    choice = []
    for c, (offset, width) in enumerate(zip(OFFSETS, WIDTHS)):
        code = (index >> offset) & ((1 << width) - 1)     # read this cube's qubits as a number
        table = FIRST_CHOICES if c == 0 else CHOICES
        choice.append(table[code] if code < len(table) else None)
    return choice


def compact_cost(choice):
    """Colour-count penalties, as in Section 4, plus PENALTY for each invalid cube.

    An invalid cube shows no colours. That keeps the cost a sum over pairs of cubes,
    so the Hamiltonian has terms with at most 3 + 3 = 6 qubits.
    """
    total = PENALTY * sum(ch is None for ch in choice)
    for side in (0, 1):                                    # 0 = front/back, 1 = left/right
        for k in COLOURS:
            d = sum(CUBES[c][ch[side]].count(k) for c, ch in enumerate(choice) if ch is not None)
            total += (d - 2) ** 2
    return total


E_COMPACT = np.array([compact_cost(compact_decode(i)) for i in range(2 ** N_COMPACT)], dtype=float)

# Classical checks: which bitstrings are valid, which cost 0, and which pass the tower check
valid = [i for i in range(2 ** N_COMPACT) if None not in compact_decode(i)]
zero = [i for i in range(2 ** N_COMPACT) if E_COMPACT[i] == 0]
passing = [i for i in valid if solves(tower_from(CUBES, compact_decode(i)))]
print(f"{N_COMPACT} qubits: {len(valid)} valid bitstrings of {2 ** N_COMPACT}")
print(f"cost 0 on {zero}; pass the tower check: {passing}; same: {zero == passing}")
print("the one answer:", compact_decode(zero[0]), "| next lowest cost:", sorted(set(E_COMPACT))[1])
COMPACT_SOLUTION = zero[0]

def hamiltonian_from_costs(costs):
    """Exact Z-only Hamiltonian whose value on bitstring i is costs[i] (fast Walsh-Hadamard transform)."""
    n = int(np.log2(len(costs)))
    coeffs = costs.astype(float).copy()
    h = 1
    while h < len(coeffs):                    # standard in-place butterfly
        for i in range(0, len(coeffs), 2 * h):
            a, b = coeffs[i:i + h].copy(), coeffs[i + h:i + 2 * h].copy()
            coeffs[i:i + h], coeffs[i + h:i + 2 * h] = a + b, a - b
        h *= 2
    coeffs /= len(costs)
    # coefficient m belongs to the product of Z on the qubits whose bit is set in m
    terms = [("Z" * bin(m).count("1"), [q for q in range(n) if m >> q & 1], c)
             for m, c in enumerate(coeffs) if abs(c) > 1e-9]
    return SparsePauliOp.from_sparse_list(terms, n).simplify()


H_compact = hamiltonian_from_costs(E_COMPACT)
sizes = [label.count("Z") for label in H_compact.paulis.to_labels()]
print(f"{len(H_compact)} Pauli terms; largest has {max(sizes)} Z's")
print(f"largest gap between H and the cost list on all 2,048 bitstrings: "
      f"{np.abs(diagonal(H_compact) - E_COMPACT).max():.1e}")

def multi_z_cost_layer(qc, H, gamma):
    """exp(-i gamma H) for a Z-only H with terms of any size."""
    for label, coeff in zip(H.paulis.to_labels(), H.coeffs):
        qubits = [q for q, op in enumerate(reversed(label)) if op == "Z"]
        if not qubits:
            continue                                        # identity term: a global phase, skip
        for a, b in zip(qubits, qubits[1:]):                # CX ladder: parity ends on the last qubit
            qc.cx(a, b)
        qc.rz(2 * gamma * coeff.real, qubits[-1])
        for a, b in reversed(list(zip(qubits, qubits[1:]))):  # undo the ladder
            qc.cx(a, b)


def compact_qaoa(H, gammas, betas):
    qc = QuantumCircuit(H.num_qubits)
    qc.h(range(H.num_qubits))
    for g, b in zip(gammas, betas):
        multi_z_cost_layer(qc, H, g)
        qc.rx(2 * b, range(H.num_qubits))
    return qc


def compact_sim(costs, gammas, betas):
    """Same circuit in plain numpy: phase each bitstring by its cost, then rotate each qubit with rx."""
    n = int(np.log2(len(costs)))
    psi = np.full(len(costs), len(costs) ** -0.5, dtype=complex)
    for g, b in zip(gammas, betas):
        psi = psi * np.exp(-1j * g * costs)
        rx = np.array([[np.cos(b), -1j * np.sin(b)], [-1j * np.sin(b), np.cos(b)]])
        t = psi.reshape([2] * n)
        for axis in range(n):
            t = np.moveaxis(np.tensordot(rx, t, axes=([1], [axis])), 0, axis)
        psi = t.reshape(-1)
    return np.abs(psi) ** 2


rng = np.random.default_rng(SEED)
g, b = rng.uniform(0, np.pi, 2), rng.uniform(0, np.pi, 2)
gap = np.abs(Statevector(compact_qaoa(H_compact, g, b)).probabilities() - compact_sim(E_COMPACT, g, b)).max()
print(f"fast simulator vs Statevector of the real circuit, p=2, random angles: {gap:.1e}")

def tune_compact(costs, p_max, grid=61, maxiter=800):
    """Same recipe as tune() in Section 7.3: grid for p = 1, then add layers with COBYLA."""
    gs, bs = np.linspace(0, np.pi, grid), np.linspace(0, np.pi, grid)
    avg = np.array([[compact_sim(costs, [g], [b]) @ costs for b in bs] for g in gs])
    i, j = np.unravel_index(avg.argmin(), avg.shape)
    gammas, betas, layers = [gs[i]], [bs[j]], []
    for p in range(1, p_max + 1):
        if p > 1:
            gammas, betas = gammas + [gammas[-1]], betas + [betas[-1]]
        result = minimize(lambda a: compact_sim(costs, a[:p], a[p:]) @ costs, gammas + betas,
                          method="COBYLA", options={"maxiter": maxiter})
        gammas, betas = list(result.x[:p]), list(result.x[p:])
        layers.append((gammas, betas))
    return layers


start = time.perf_counter()
COMPACT_LAYERS = tune_compact(E_COMPACT, p_max=20)
print(f"tuned p = 1 to 20 in {time.perf_counter() - start:.0f} s\n")
print(" p   P(correct tower)   P(valid code)   CX gates   depth")
for p, (g, b) in enumerate(COMPACT_LAYERS, start=1):
    if p in (1, 2, 4, 8, 12, 16, 20):
        probs = compact_sim(E_COMPACT, g, b)
        cx, depth = circuit_size(compact_qaoa(H_compact, g, b))
        print(f"{p:>2}   {probs[COMPACT_SOLUTION]:>16.1%}   {probs[valid].sum():>13.0%}   {cx:>8}   {depth:>5}")

g20, b20 = COMPACT_LAYERS[19]
exact = compact_sim(E_COMPACT, g20, b20)[COMPACT_SOLUTION]
counts = run_on_qbraid(compact_qaoa(H_compact, g20, b20), shots=1000)

correct = valid_shots = 0
for bitstring, n in counts.items():
    choice = compact_decode(int(bitstring, 2))       # Qiskit order: int() reads qubit 0 as the last character
    if None not in choice:
        valid_shots += n
        correct += n * solves(tower_from(CUBES, choice))
shots = sum(counts.values())
print(f"11 qubits, p=20, {shots} shots on local Aer: {correct / shots:.1%} correct towers (exact {exact:.1%}), "
      f"{valid_shots / shots:.0%} of shots valid in every cube")
