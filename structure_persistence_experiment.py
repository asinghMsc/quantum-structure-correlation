"""
Structure Persistence Protocol (Qiskit Implementation)
------------------------------------------------------
Core experiment comparing structured vs random circuit decay under interference.
Used for: Structured Correlation Levels After Partial Time Reversal (Singh, 2026)
"""

import numpy as np
import json
from datetime import datetime
from typing import Tuple, List, Dict

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector, partial_trace, entropy, state_fidelity

# Global Params
CONFIG = {
    "n_qubits": 8,                    # 4+4 partition
    "n_qubits_A": 4,
    "n_qubits_B": 4,
    "circuit_depth": 12,
    "n_random_trials": 100,           # Baseline count
    "n_experiment_trials": 100,       # Repeats
    "reversal_fraction": 0.33,
    "perturbation_sigma": 0.1,        # Rotation noise floor
    "random_seed": 42,
    "apply_noise": False,
    "p1_error": 0.001,
    "p2_error": 0.01,
}

# --- Circuit Logic ---

def create_structured_circuit(config: dict, seed: int) -> QuantumCircuit:
    """Constructs a circuit with hardcoded Bell pairs followed by local scrambling."""
    np.random.seed(seed)
    n = config["n_qubits"]
    n_A = config["n_qubits_A"]
    
    qc = QuantumCircuit(n)
    
    # Init: 4 Bell pairs across the A/B cut.
    # Note: H only on subsystem A to avoid product states.
    for i in range(n_A):
        qc.h(i)
        qc.cx(i, i + n_A)
    
    qc.barrier()
    
    # 6 Layers of local rotations (parameterised evolution)
    for _ in range(6):
        angles_y = np.random.uniform(0, 2 * np.pi, n)
        angles_z = np.random.uniform(0, 2 * np.pi, n)
        for i in range(n):
            qc.ry(angles_y[i], i)
            qc.rz(angles_z[i], i)
        qc.barrier()
    
    # 3 Layers of internal CZs (intra-subsystem correlation)
    for _ in range(3):
        for i in range(n_A - 1): qc.cz(i, i + 1)
        for i in range(n_A, n - 1): qc.cz(i, i + 1)
        qc.barrier()
    
    return qc

def create_randomised_circuit(config: dict, seed: int) -> QuantumCircuit:
    """Matched depth baseline but with random gate selection."""
    np.random.seed(seed)
    n = config["n_qubits"]
    qc = QuantumCircuit(n)
    
    # Scrambled start
    for i in range(n):
        qc.ry(np.random.uniform(0, 2 * np.pi), i)
        qc.rz(np.random.uniform(0, 2 * np.pi), i)
    
    # Non-structured 2-qubit gates
    pairs = list(range(n))
    np.random.shuffle(pairs)
    for i in range(0, n - 1, 2):
        qc.cx(pairs[i], pairs[i + 1])
    
    qc.barrier()
    
    # Mid-layers
    for _ in range(6):
        for i in range(n):
            qc.ry(np.random.uniform(0, 2 * np.pi), i)
            qc.rz(np.random.uniform(0, 2 * np.pi), i)
        qc.barrier()
    
    # Final internal scrambling
    for _ in range(3):
        pairs = list(range(n))
        np.random.shuffle(pairs)
        for i in range(0, n - 1, 2):
            qc.cz(pairs[i], pairs[i + 1])
        qc.barrier()
    
    return qc

def create_self_referential_circuit(config: dict, seed: int) -> QuantumCircuit:
    """Variant with mid-circuit feedforward to test non-local effects."""
    np.random.seed(seed)
    n_A = config["n_qubits_A"]
    qc = QuantumCircuit(config["n_qubits"])
    cr = ClassicalRegister(2, 'ff')
    qc.add_register(cr)
    
    # Bell pairs
    for i in range(n_A):
        qc.h(i); qc.cx(i, i + n_A)
    qc.barrier()
    
    # Partial measure + feedforward
    qc.measure(0, cr[0]); qc.measure(4, cr[1])
    qc.x(1).c_if(cr[0], 1)
    qc.z(5).c_if(cr[1], 1)
    qc.barrier()
    
    # Standard tail
    for _ in range(6):
        for i in range(config["n_qubits"]):
            qc.ry(np.random.uniform(0, 2 * np.pi), i)
            qc.rz(np.random.uniform(0, 2 * np.pi), i)
        qc.barrier()
    
    for _ in range(3):
        for i in range(n_A - 1): qc.cz(i, i + 1)
        for i in range(n_A, config["n_qubits"] - 1): qc.cz(i, i + 1)
        qc.barrier()
    
    return qc

# --- Analysis & Metrics ---

def apply_partial_time_reversal(qc: QuantumCircuit, config: dict, seed: int) -> QuantumCircuit:
    """Applies local interference: partial inverse + random rotation noise."""
    np.random.seed(seed + 1000)
    n_A = config["n_qubits_A"]
    qc_interference = qc.copy()
    
    # Reverse final 3 layers (CZ is own inverse)
    for _ in range(3):
        qc_interference.barrier()
        for i in range(n_A - 1): qc_interference.cz(i, i + 1)
        for i in range(n_A, config["n_qubits"] - 1): qc_interference.cz(i, i + 1)
    
    qc_interference.barrier()
    
    # Injection of perturbation noise
    sigma = config["perturbation_sigma"]
    for i in range(config["n_qubits"]):
        qc_interference.rx(np.random.normal(0, sigma), i)
        qc_interference.ry(np.random.normal(0, sigma), i)
        qc_interference.rz(np.random.normal(0, sigma), i)
    
    return qc_interference

def compute_mutual_information(sv: Statevector, config: dict) -> float:
    """Calculates I(A;B) = S(A) + S(B) - S(AB). Standard little-endian trace."""
    n_B, n_A = config["n_qubits_B"], config["n_qubits_A"]
    rho_A = partial_trace(sv, list(range(n_B))).data
    rho_B = partial_trace(sv, list(range(n_B, n_A + n_B))).data
    
    S_A = entropy(rho_A, base=2)
    S_B = entropy(rho_B, base=2)
    S_AB = entropy(sv.to_operator().data, base=2)
    
    return float(S_A + S_B - S_AB)

# --- Runners ---

def run_single_experiment(ctype: str, config: dict, seed: int) -> dict:
    """Main trial logic: build -> benchmark -> perturb -> re-measure."""
    qc = create_structured_circuit(config, seed) if ctype == "structured" else \
         create_randomised_circuit(config, seed)
    
    sv_pre = Statevector.from_instruction(qc)
    mi_pre = compute_mutual_information(sv_pre, config)
    
    qc_post = apply_partial_time_reversal(qc, config, seed)
    sv_post = Statevector.from_instruction(qc_post)
    mi_post = compute_mutual_information(sv_post, config)
    
    f = state_fidelity(sv_pre, sv_post)
    r = mi_post / mi_pre if mi_pre > 1e-10 else 0.0
    
    return {"type": ctype, "seed": seed, "mi_pre": mi_pre, "mi_post": mi_post, "R": r, "F": f}

def run_full_experiment(config: dict) -> dict:
    """Wraps batch trials for both conditions."""
    print(f"Starting {config['n_experiment_trials']} trials...")
    res = {"config": config, "ts": datetime.now().isoformat(), "structured": [], "randomised": []}
    
    for i in range(config["n_experiment_trials"]):
        res["structured"].append(run_single_experiment("structured", config, config["random_seed"] + i))
        res["randomised"].append(run_single_experiment("randomised", config, config["random_seed"] + 10000 + i))
        if (i + 1) % 25 == 0: print(f"  {i+1}/{config['n_experiment_trials']} done")
        
    return res

def compute_statistics(results: dict) -> dict:
    """Summary stats + z-scores for result differentiation."""
    def get_stats(arr): return {"mean": float(np.mean(arr)), "std": float(np.std(arr))}
    
    s_mi = [r["mi_post"] for r in results["structured"]]
    r_mi = [r["mi_post"] for r in results["randomised"]]
    
    mu_r, sigma_r = np.mean(r_mi), np.std(r_mi)
    z_i = (np.mean(s_mi) - mu_r) / sigma_r if sigma_r > 1e-10 else 0
    
    return {
        "structured": {"mi_post": get_stats(s_mi)},
        "randomised": {"mi_post": get_stats(r_mi)},
        "z_score": float(z_i)
    }

if __name__ == "__main__":
    raw = run_full_experiment(CONFIG)
    stats = compute_statistics(raw)
    
    print("\n--- Summary ---")
    print(f"Structured MI: {stats['structured']['mi_post']['mean']:.3f} bits")
    print(f"Randomised MI: {stats['randomised']['mi_post']['mean']:.3f} bits")
    print(f"Z-score:       {stats['z_score']:.3f}")
    
    with open("experiment_results.json", "w") as f:
        json.dump({"stats": stats, "cfg": CONFIG}, f, indent=2)
    print("\nFile 'experiment_results.json' updated.")
