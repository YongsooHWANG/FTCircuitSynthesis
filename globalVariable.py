
# -*-coding:utf-8-*-
# from __future__ import unicode_literals
# version 0.5

import re

from collections import OrderedDict

str_module = 'module'
str_qubit_array = 'qbit*'
str_qubit_single = 'qbit'
str_cbit_single = 'cbit'

str_gate_h = 'H'
str_gate_x = 'X'
str_gate_z = 'Z'
str_gate_y = 'Y'
str_gate_yi16 = 'Y_i16'

str_gate_i = 'I'
str_gate_t = 'T'
str_gate_tdag = 'Tdag'
str_gate_s = 'S'
str_gate_sdag = 'Sdag'
str_gate_rz = 'Rz'
str_gate_rx = 'Rx'
str_gate_ry = 'Ry'
str_gate_sx = 'SX'
str_gate_phase = 'P'
str_gate_u = "U"

str_gate_cnot = 'CNOT'
str_gate_cphase = 'CP'
str_gate_lcnot = 'LCNOT'

str_gate_cx = 'CX'
str_gate_cz = 'CZ'

str_gate_swap = 'SWAP'
str_gate_lswap = 'LSWAP'

str_gate_cnotv = 'CNOTV'
str_gate_cnoth = 'CNOTH'

str_gate_swapv = 'SWAPV'
str_gate_swaph = 'SWAPH'

str_gate_prepz = 'PrepZ'
str_gate_measz = 'MeasZ'

str_gate_prepx = 'PrepX'
str_gate_measx = 'MeasX'

str_gate_pass = 'Pass'
str_gate_idle = 'Id'

str_smooth_merge = "SMerge"
str_smooth_split = "SSplit"

str_rough_merge = "RMerge"
str_rough_split = "RSplit"

str_distillation_A = 'DistillationA'
str_distillation_Y = 'DistillationY'

str_QEC = 'QEC'

str_barrier_all = "Barrier-All"
str_barrier = "Barrier"

# operation to make two qubits in neighborhood
str_adjoin = 'Adjoin'

str_interCNOT = 'InterCNOT'
str_innerSWAP = 'InnerSWAP'

# move a qubit (with qubit name) to a certain qubit position (of qubit idx)
str_move = 'MOVE'
str_move_back = 'MoveBack'
str_braid = 'Braid'

# prepare for logical CNOT operation
str_prepare_cnot = "PrepCNOT"

# physical operation
str_physical_h = '_H'
str_physical_x = '_X'
str_physical_z = '_Z'
str_physical_y = '_Y'

str_physical_t = '_T'
str_physical_tdag = '_Tdag'
str_physical_s = '_S'
str_physical_sdag = '_Sdag'
str_physical_rz = '_Rz'

str_physical_cnot = '_CNOT'
str_physical_swap = '_SWAP'

str_physical_measz = '_MeasZ'
str_physical_prepz = '_PrepZ'

str_physical_measx = '_MeasX'
str_physical_prepx = '_PrepX'

surface_code_property = None


# device_type
IBM = 1
Rigetti = 2
Other = 3

# type of qubits: local qubits or parameter qubits
LOCAL = 1
PARAM = 0
BOTH = 2
DUMMY=1000

# type of function: gate or a user defined module
GATE = 99
MODULE = 199

# direction on the qubit lattice
VERTICAL = 10
HORIZONTAL = 20
RIGHT = 100
LEFT = 200
UP = 300
DOWN = 400

# type of qubits for cnot gate: control qubit or target qubit
CTRL = 1000
TRGT = 2000

# direction of teleportation for calling a module
# forward: teleportation from a current module to a target module
# backward: teleportation from a target module to a current module
FORWARD = 10000
BACKWARD = 20000

# type of codes for reading file: 
# QASM file: input to this program
# system code file: output of this program
QASM = 5
SYSCODE = 6

# type of program operation
# buildup: system code generation
# execution: execution from the generated system code files
# analysis: error analysis and statistics analysis
BUILDUP = 0
EXECUTION = 1
ANALYSIS = 2

# options for system synthesis
FindMaxTError = 0
OneTimeSynthesis = 1
ObjectiveFidelity = 2

# modules layout
# ModuleLayout=0
OneDimension = 1
TwoDimension = 2

number_of_modules = 0

max_len_module_name = 0
max_len_qubit_name = 0

# list for one qubit gates and two qubit gates
list_one_qubit_gates = []
list_two_qubit_gates = []
list_nontransversal_gate = []

# dictionary for qubits and cbits for each module
dic_module_qubits = {}
dic_module_cbits = {}

dic_required_qubits = {}

dic_module_idx_key = {}
dic_module_idx_value = {}

dic_gate_property = {}

dic_module_parameter_qubits = {}
dic_parameter_passing_qubit_size = {}
dic_total_param_qubits = {}

list_gates = {}
list_physical_gates = {}

synthesis_option = {}
file_path_args = {}

module_instance = {}

dic_module_qubit_fidelity = {}

table_connectivity_graph_id = {}
table_module_to_graph_node = {}

DoubleDefect = 0
Planar = 1
Dislocation = 2

# ABB 관련 device & code 정보
list_quantum_devices = ["ION", "SC", "Superconductor", "QD", "Quantum Dot"]
list_quantum_codes = ["Steane", "Bacon-Shor", "Surface_defect", "Surface_planar"]


def initialize_globals(quantum_code=None):

	global list_one_qubit_gates
	global list_two_qubit_gates
	global list_nontransversal_gate
	global list_function_modules		# modules work like a one-qubit function


	# gate classification: one qubit gate, two qubit gate and quantum operation
	list_one_qubit_gates = set([str_gate_h, str_gate_x, str_gate_z, str_gate_y, str_gate_t, str_gate_tdag, 
		str_gate_phase, str_gate_u, str_gate_sx, str_gate_rx, str_gate_ry,
		str_gate_s, str_gate_sdag, str_gate_rz, str_gate_i, str_gate_prepz, str_gate_prepx, str_gate_measz, str_gate_measx])

	list_two_qubit_gates = set([str_gate_cnot, str_gate_cnoth, str_gate_cnotv, str_gate_cx, str_gate_cz,
		str_gate_cphase,
		str_gate_swap, str_gate_swaph, str_gate_swapv, str_move, str_move_back, str_adjoin, str_interCNOT])

	list_operations = set([str_gate_prepz, str_gate_idle])

	list_function_modules = set(["DecomposeRotation", "ControlledPhase"])
	
	if quantum_code:
		print(" The quantum code is {0}".format(quantum_code))

		if "Steane" in quantum_code:
			list_nontransversal_gate = set([str_gate_t, str_gate_tdag])
		
		elif "Bacon-Shor" in quantum_code:
			list_nontransversal_gate = set([str_gate_t, str_gate_tdag])
		
		elif quantum_code in ["Surface_defect", "Surface_planar"]:
			list_nontransversal_gate = set([str_gate_t, str_gate_tdag, str_gate_s, str_gate_sdag])

		print(" The list of non-transversal gate is {0}".format(list_nontransversal_gate))

	# else:
	# 	print(" No quantum code is chosen. ")
		
def set_gate_time(list_gates):
    global dic_gate_property

    for i, gate in enumerate(list_gates):
        dic_gate_property[gate[0]] = (gate[1].time, gate[1].success_prob)

