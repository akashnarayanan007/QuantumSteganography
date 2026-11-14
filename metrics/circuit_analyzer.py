"""
Quantum Circuit Analyzer and Complexity Profiler.
Quantifies circuit depth, qubit resource count, gate distributions,
and estimates theoretical circuit fidelity under noise.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from qiskit import QuantumCircuit


@dataclass
class CircuitReport:
    """Dataclass holding quantum circuit profiling metrics."""
    num_qubits: int
    total_gates: int
    circuit_depth: int
    num_cx_gates: int
    num_x_gates: int
    num_h_gates: int
    num_mcx_gates: int
    t_gate_count: int
    estimated_fidelity: float
    gate_distribution: Dict[str, int] = field(default_factory=dict)


class CircuitAnalyzer:
    """
    Analyzes and reports quantum circuit metrics.
    """

    def analyze(self, circuit: QuantumCircuit, noise_per_layer: float = 0.0005) -> CircuitReport:
        """
        Extract detailed quantum complexity metrics from a QuantumCircuit object.
        """
        gate_counts = dict(circuit.count_ops())
        num_qubits = circuit.num_qubits
        total_gates = sum(gate_counts.values())
        depth = circuit.depth()

        num_cx = gate_counts.get("cx", 0)
        num_x = gate_counts.get("x", 0)
        num_h = gate_counts.get("h", 0)
        num_mcx = gate_counts.get("mcx", 0)
        num_t = gate_counts.get("t", 0) + gate_counts.get("tdg", 0)

        # Estimated theoretical circuit fidelity = (1 - ε)^depth
        estimated_fidelity = max(0.0, min(1.0, (1.0 - noise_per_layer) ** depth))
        estimated_fidelity = round(estimated_fidelity, 4)

        return CircuitReport(
            num_qubits=num_qubits,
            total_gates=total_gates,
            circuit_depth=depth,
            num_cx_gates=num_cx,
            num_x_gates=num_x,
            num_h_gates=num_h,
            num_mcx_gates=num_mcx,
            t_gate_count=num_t,
            estimated_fidelity=estimated_fidelity,
            gate_distribution=gate_counts,
        )

    def print_report(self, report: CircuitReport) -> None:
        """
        Print a formatted CLI summary of circuit metrics.
        """
        print("  ┌──────────────────────────────────────────────┐")
        print("  │         QUANTUM CIRCUIT ANALYSIS             │")
        print("  ├──────────────────────────────────────────────┤")
        print(f"  │  Total Qubits      : {report.num_qubits:<24}│")
        print(f"  │  Circuit Depth     : {report.circuit_depth:<24}│")
        print(f"  │  Total Gate Count  : {report.total_gates:<24}│")
        print(f"  │  Hadamard (H) Gates: {report.num_h_gates:<24}│")
        print(f"  │  Pauli-X Gates     : {report.num_x_gates:<24}│")
        print(f"  │  CNOT (CX) Gates   : {report.num_cx_gates:<24}│")
        print(f"  │  Multi-CX (MCX)    : {report.num_mcx_gates:<24}│")
        print(f"  │  Estimated Fidelity: {report.estimated_fidelity * 100:.2f}%{'':<18}│")
        print("  └──────────────────────────────────────────────┘")
