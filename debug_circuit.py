"""
Diagnostic: Endianness & Entropy
--------------------------------
Tracing the MI preservation through the circuit layers 
to verify little-endian qubit mapping.
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, partial_trace, entropy

def get_stats(sv):
    r_a = partial_trace(sv, [4,5,6,7]).data
    r_b = partial_trace(sv, [0,1,2,3]).data
    return entropy(r_a, 2), entropy(r_b, 2), entropy(sv, 2)

# Step 1: Baseline Bell pairs
qc = QuantumCircuit(8)
for i in range(4):
    qc.h(i)
    qc.cx(i, i+4)

sv = Statevector.from_instruction(qc)
s_a, s_b, s_ab = get_stats(sv)
print(f"Init (Bell Pairs): S(A)={s_a:.2f}, S(B)={s_b:.2f}, I(A;B)={s_a+s_b-s_ab:.2f}")

# Step 2: Random local rotations
np.random.seed(42)
for i in range(8):
    qc.ry(np.random.uniform(0, 2*np.pi), i)
    qc.rz(np.random.uniform(0, 2*np.pi), i)

sv_rot = Statevector.from_instruction(qc)
s_a, s_b, s_ab = get_stats(sv_rot)
print(f"Post-Rotations:    S(A)={s_a:.2f}, S(B)={s_b:.2f}, I(A;B)={s_a+s_b-s_ab:.2f}")

# Step 3: Intra-subsystem gates
for i in range(3): qc.cz(i, i+1)
for i in range(4, 7): qc.cz(i, i+1)

sv_final = Statevector.from_instruction(qc)
s_a, s_b, s_ab = get_stats(sv_final)
print(f"Post-Internal CZ: S(A)={s_a:.2f}, S(B)={s_b:.2f}, I(A;B)={s_a+s_b-s_ab:.2f}")

print("\nConclusion: MI is invariant if local gate logic holds.")
