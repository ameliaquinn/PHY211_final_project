# import packages
import numpy as np

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import EstimatorV2 as Estimator

from matplotlib import pyplot as plt
from matplotlib import ticker as tck


# Sets up the backend service
# Parameters: your IBM token and instance of your account in order to connect to the IBM hardware
# as well as the minimum number of qubits you will need (int)
# Returns the machine that will be used to run the program
def backend_setup(token, instance, min_num_qubits):
    if not isinstance(token, str):
        raise ValueError(f"Token must be a string, got: {token}")
    if not isinstance(instance, str):
        raise ValueError(f"Instance must be a string, got: {instance}")
    if not isinstance(min_num_qubits, int) or min_num_qubits < 1:
        raise ValueError(f"Minimum qubit number must be a positive integer, got: {min_num_qubits}")
    QiskitRuntimeService.save_account(token = token, instance = instance, overwrite = True)
    service = QiskitRuntimeService()
    backend = service.least_busy(operational = True, simulator = False, min_num_qubits = min_num_qubits)
    print(backend.name)
    return backend


# This function requires no imput, simply sets up the CHSH circuit we will use for the experiment and returns it
def setup_chsh_circuit():
    theta = Parameter('$\\theta$')
    chsh_circuit = QuantumCircuit(2)
    chsh_circuit.h(0)
    chsh_circuit.cx(0,1)
    chsh_circuit.ry(theta,0)
    return chsh_circuit


# This is where we set up our phase array
# Parameters: the desired number of phases from 0 to 2pi (int)
# Returns: phases (which is an array of phases) and then individual_phases which puts the array into list form (needed for IBM documentation)
def make_phases(number_of_phases):
    if not isinstance(number_of_phases, int) or number_of_phases < 1:
        raise ValueError(f"Number of phases must be a positive integer, got: {number_of_phases}")
    phases = np.linspace(0, 2 * np.pi, number_of_phases)
    individual_phases = [[ph] for ph in phases]
    return phases, individual_phases


def make_observables(state1, state2, state3, state4):
    if not isinstance(state1, str) or not isinstance(state2, str) or not isinstance(state3, str) or not isinstance(state4, str):
        raise ValueError("At least one of your states is not a string -- they must all be strings!")
    observable1 = SparsePauliOp.from_list([(state1, 1), (state2, -1), (state3, 1), (state4, 1)])
    observable2 = SparsePauliOp.from_list([(state1, 1), (state2, 1), (state3, -1), (state4, 1)])
    return observable1, observable2



# This function takes in the CHSH circuit, backend, and desired optimization level
# It then passes the circuit through IBM's built-in generate passmanager in order to generate a circuit obeying Instruction Set Architecture (ISA)
# Returns the ISA circuit
def make_isa_circuit(chsh_circuit, backend, optimization_level):
    if not isinstance(optimization_level, int):
        raise ValueError(f"Optimization level must be an integer, got: {optimization_level}")
    target = backend.target
    pm = generate_preset_pass_manager(target = target, optimization_level = optimization_level)
    chsh_isa_circuit = pm.run(chsh_circuit)
    return chsh_isa_circuit


# This function plots the results of both CHSH quantities from 0 to 2pi, including the classical and quantum bounds on the plot
def plot_results(phases, chsh1_est, chsh2_est):
    fig, ax = plt.subplots(figsize = (10,6))

    # results from hardware
    ax.plot(phases / np.pi, chsh1_est, "o-", label = "CHSH1", zorder = 3)
    ax.plot(phases / np.pi, chsh2_est, "o-", label = "CHSH2", zorder = 3)

    # classical bound
    ax.axhline(y = 2, color = "0.9", linestyle = "--")
    ax.axhline(y = -2, color = "0.9", linestyle = "--")

    # quantum bound
    ax.axhline(y = np.sqrt(2) * 2, color = "0.9", linestyle = "-.")
    ax.axhline(y = -np.sqrt(2) * 2, color = "0.9", linestyle = "-.")
    ax.fill_between(phases / np.pi, 2, 2 * np.sqrt(2), color = "0.6", alpha = 0.7)
    ax.fill_between(phases / np.pi, -2, -2 * np.sqrt(2), color = "0.6", alpha = 0.7)

    # labels and legend
    plt.xlabel("Theta")
    plt.ylabel("CHSH witness")
    plt.legend()
    plt.show()


# This function runs the entire experiment from start to finish, with my recommended values for the experiment!
def main():
    my_token = "itd8Yf4W2boZsNpZnn7rfPXs7L7z8AhSigm9ZYdAEcIN"
    my_instance = "crn:v1:bluemix:public:quantum-computing:us-east:a/8291768cb13d4fcb8bee320022d597e8:e1752a2c-f2bc-4054-adc5-ac56c0b76a1e::"
    my_min_num_qubits = 127
    backend = backend_setup(my_token, my_instance, my_min_num_qubits)

    chsh_circuit = setup_chsh_circuit()
    chsh_circuit.draw(output = "mpl", idle_wires = False, style = "iqp")

    phases, individual_phases = make_phases(21)

    observable1, observable2 = make_observables("ZZ", "ZX", "XZ", "XX")

    chsh_isa_circuit = make_isa_circuit(chsh_circuit, backend, 3)
    chsh_isa_circuit.draw(output = "mpl", idle_wires = False, style = "iqp")

    isa_observable1 = observable1.apply_layout(layout = chsh_isa_circuit.layout)
    isa_observable2 = observable2.apply_layout(layout = chsh_isa_circuit.layout)

    estimator = Estimator(mode = backend)
    pub = (
        chsh_isa_circuit,
        [[isa_observable1], [isa_observable2]],
        individual_phases,
    )

    job_result = estimator.run(pubs = [pub]).result()

    chsh1_est = job_result[0].data.evs[0]
    chsh2_est = job_result[0].data.evs[1]

    plot_results(phases, chsh1_est, chsh2_est)