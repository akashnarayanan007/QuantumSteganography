"""
Quantum Simulator Backend Wrapper.
Supports ideal statevector simulation (exact amplitude propagation)
and realistic noisy simulation with depolarizing error models.
"""

from typing import Union, Any, Dict, Optional
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


class QuantumSimulator:
    """
    Simulation engine for quantum image processing circuits.
    """

    def __init__(self, config: Union[dict, Any] = None):
        if config is not None:
            if isinstance(config, dict):
                q_cfg = config.get("quantum", {})
                self.backend_type = str(q_cfg.get("backend", "statevector"))
                self.shots = int(q_cfg.get("shots", 8192))
                self.noise_level = float(q_cfg.get("noise_level", 0.001))
            else:
                self.backend_type = str(getattr(config.quantum, "backend", "statevector"))
                self.shots = int(getattr(config.quantum, "shots", 8192))
                self.noise_level = float(getattr(config.quantum, "noise_level", 0.001))
        else:
            self.backend_type = "statevector"
            self.shots = 8192
            self.noise_level = 0.001

        self._init_backend()

    def _init_backend(self) -> None:
        """Initialize Qiskit Aer backend based on configuration."""
        try:
            from qiskit_aer import AerSimulator
            if self.backend_type == "noisy":
                from qiskit_aer.noise import NoiseModel, depolarizing_error
                noise_model = NoiseModel()
                error_1q = depolarizing_error(self.noise_level, 1)
                error_2q = depolarizing_error(self.noise_level * 2, 2)
                noise_model.add_all_qubit_quantum_error(error_1q, ["u", "x", "h"])
                noise_model.add_all_qubit_quantum_error(error_2q, ["cx", "mcx"])
                self.backend = AerSimulator(noise_model=noise_model)
            else:
                self.backend = AerSimulator(method="statevector")
        except ImportError:
            # Fallback if aer is not available in basic statevector tests
            self.backend = None

    def run_statevector(self, circuit: QuantumCircuit) -> Statevector:
        """
        Compute the pure statevector from a quantum circuit (ignoring measurements).
        """
        # Create a copy with measurement operations stripped
        clean_circ = circuit.copy()
        clean_circ.remove_final_measurements(inplace=True)

        # Statevector.from_instruction computes exact mathematical state
        sv = Statevector.from_instruction(clean_circ)
        return sv

    def run_shots(self, circuit: QuantumCircuit, shots: Optional[int] = None) -> Dict[str, int]:
        """
        Execute measurement sampling over specified shots.
        """
        num_shots = shots or self.shots
        meas_circ = circuit.copy()
        meas_circ.measure_all()

        if self.backend is None:
            self._init_backend()

        if self.backend is not None:
            job = self.backend.run(meas_circ, shots=num_shots)
            result = job.result()
            return result.get_counts()
        else:
            # Fallback to statevector sampling
            sv = self.run_statevector(circuit)
            probs = sv.probabilities_dict()
            counts: Dict[str, int] = {}
            for k, p in probs.items():
                c = int(round(p * num_shots))
                if c > 0:
                    counts[k] = c
            return counts

    def get_statevector_array(self, sv: Union[Statevector, np.ndarray]) -> np.ndarray:
        """
        Return statevector amplitude array as complex numpy array.
        """
        if isinstance(sv, Statevector):
            return np.asarray(sv.data, dtype=np.complex128)
        return np.asarray(sv, dtype=np.complex128)
