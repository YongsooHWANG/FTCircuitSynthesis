
import re
import collections
import parse
import globalVariable as g
from icecream import ic

from math import *

get_bigger = lambda a, b: a if a > b else b
get_smaller = lambda a, b: a if a < b else b

parser = re.compile("[\{\[\]a-zA-Z0-9_.*/\->\+}]+")


def analyze_qasm(path_QASM):
	"""
		function to extract list_qasm_commands, list_algorithm_qubits from QASM
	"""
	list_qasm_commands = []
	list_algorithm_qubits = []
	
	cnot_counts = 0
		
	with open(path_QASM, "r") as infile:
		for line in infile:
			token = parser.findall(line)
			if not len(token): continue
			list_qasm_commands.append(token)

			if token[0] in [g.str_gate_rx, g.str_gate_rz, g.str_gate_ry]: 
				# 경우에 따라서 gate angle trgt 순으로 기재된 qasm 과 gate trgt angle 로 기재된 qasm 이 혼재함
				try:
					if type(eval(token[1])) in [float, int]: angle, trgt = token[1:3]
										
				except: 
					if type(eval(token[2])) in [float, int]: trgt, angle = token[1:3]

				finally:
					list_algorithm_qubits.append(trgt)

			elif token[0] in [g.str_gate_prepz, g.str_gate_prepx, g.str_gate_measz, g.str_gate_measx]:
				list_algorithm_qubits.append(token[1])

			elif token[0] in [g.str_gate_x, g.str_gate_z, g.str_gate_y, g.str_gate_phase, g.str_gate_h]:
				list_algorithm_qubits.append(token[1])

			elif token[0] in [g.str_gate_cnot]: 
				cnot_counts+=1
				list_algorithm_qubits.extend(list(token[1:]))

			elif token[0] in [g.str_gate_swap]: 
				cnot_counts+=3
				list_algorithm_qubits.extend(list(token[1:]))

			elif token[0] in ["Qubit"]:
				result = parse.compile("{}[{}]").parse(token[1])
				if result is None:
					list_algorithm_qubits.append(token[1])
				else:
					trgt_qubit_name, trgt_qubit_size = result[:]

					if trgt_qubit_size.isdigit():
						for i in range(len(trgt_qubit_size)):
							list_algorithm_qubits.append("{}[{}]".format(trgt_qubit_name, i))
					

	if not len(list_algorithm_qubits):
		with open(path_QASM, "r") as infile:
			for line in infile:
				token = parser.findall(line)
				if not len(token): continue

				if token[0] in [g.str_gate_rx, g.str_gate_rz, g.str_gate_ry]: 
					try:
						if type(eval(token[1])) == float: angle, trgt = token[1:3]
					except: 
						if type(eval(token[2])) == float: trgt, angle = token[1:3]
					finally:
						list_algorithm_qubits.append(trgt)
				
				elif token[0] in [g.str_gate_prepz, g.str_gate_prepx, g.str_gate_measz, g.str_gate_measx]:
					list_algorithm_qubits.append(token[1])

				elif token[0] in [g.str_gate_x, g.str_gate_z, g.str_gate_y, g.str_gate_phase, g.str_gate_h]:
					list_algorithm_qubits.append(token[1])

				elif token[0] in [g.str_gate_cnot]: 
					cnot_counts+=1
					list_algorithm_qubits.extend(list(token[1:]))

				elif token[0] in [g.str_gate_swap]: 
					cnot_counts+=3
					list_algorithm_qubits.extend(list(token[1:]))

	list_algorithm_qubits = list(set(list_algorithm_qubits))

	return list_qasm_commands, list_algorithm_qubits, cnot_counts




def evaluate_syscode(system_code, **kwargs):
	"""

	"""
	performance_criterion = kwargs.get("criterion")
	qchip_data = kwargs.get("qchip_data")
	if qchip_data is None: 
		raise error.Error("qchip data is not provided.")
	flag_single_qubit = kwargs.get("single_qubit")

	if flag_single_qubit is None: flag_single_qubit = False
	flag_measurement = kwargs.get("measurement")
	if flag_measurement is None: flag_measurement = False

	# performance criterion 1
	# gates: the number of quantum gates (usually swap)
	if performance_criterion == "cnot":
		count_cnot = 0
		for inst in system_code:
			if inst[0] == g.str_gate_swap: count_cnot+=3
			elif inst[0] in [g.str_gate_cnot, g.str_gate_cz]: count_cnot+=1

		return count_cnot

	# performance criterion 2
	# circuit depth	
	elif performance_criterion == "depth":
		qubit_depth = collections.defaultdict(int)
		
		for inst in system_code:
			if inst[0] in [g.str_gate_swap, g.str_gate_cnot, g.str_gate_cz]:
				ctrl, trgt = inst[1:3]
				last_step = get_bigger(qubit_depth[ctrl], qubit_depth[trgt])
				qubit_depth[ctrl] = qubit_depth[trgt] = last_step + 1

			elif inst[0] in [g.str_gate_rx, g.str_gate_rz, g.str_gate_ry]:
				qubit = inst[2]
				qubit_depth[qubit]+=1

			else:
				qubit = inst[1]
				qubit_depth[qubit]+=1

		return max(list(qubit_depth.values()))

	# performance criterion 3
	# circuit execution time
	elif performance_criterion == "time":
		qubit_time = collections.defaultdict(float)
		# measurement 시간 반영
		if flag_measurement and qchip_data.get("measure_time") is not None:
			for inst in system_code:
				if inst[0] in [g.str_gate_cnot, g.str_gate_cz]:
					ctrl, trgt = inst[1:3]
					last_time = get_bigger(qubit_time[ctrl], qubit_time[trgt])
					gate_time = qchip_data["net_cnot_time"][ctrl][trgt]
					qubit_time[ctrl] = qubit_time[trgt] = last_time + gate_time

				elif inst[0] == g.str_gate_swap:
					ctrl, trgt = inst[1:3]
					last_time = get_bigger(qubit_time[ctrl], qubit_time[trgt])
					gate_time = qchip_data["net_cnot_time"][ctrl][trgt] * 3
					qubit_time[ctrl] = qubit_time[trgt] = last_time + gate_time

				elif inst[0] == g.str_gate_measz:
					qubit = inst[1]
					gate_time = qchip_data["measure_time"][qubit]
					qubit_time[qubit] += gate_time
		
		# measurement 시간 미반영
		else:
			for inst in system_code:
				if inst[0] in [g.str_gate_cnot, g.str_gate_cz]:
					ctrl, trgt = inst[1:3]
					last_time = get_bigger(qubit_time[ctrl], qubit_time[trgt])
					gate_time = qchip_data["net_cnot_time"][ctrl][trgt]
					qubit_time[ctrl] = qubit_time[trgt] = last_time + gate_time

				elif inst[0] == g.str_gate_swap:
					ctrl, trgt = inst[1:3]
					last_time = get_bigger(qubit_time[ctrl], qubit_time[trgt])
					gate_time = qchip_data["net_cnot_time"][ctrl][trgt] * 3
					qubit_time[ctrl] = qubit_time[trgt] = last_time + gate_time

		return max(list(qubit_time.values()))
		
	elif performance_criterion == "fidelity":
		qubit_fidelity = {qubit: 1 for qubit in qchip_data["qubit_connectivity"].keys()}
		if flag_measurement and qchip_data.get("measure_error") is not None:
			for inst in system_code:
				if inst[0] in [g.str_gate_cnot, g.str_gate_cz]:
					ctrl, trgt = inst[1:3]
					last_fidelity = get_smaller(qubit_fidelity[ctrl], qubit_fidelity[trgt])
					gate_fidelity = qchip_data["net_cnot_error"][ctrl][trgt]
					qubit_fidelity[ctrl] = qubit_fidelity[trgt] = last_fidelity * gate_fidelity

				elif inst[0] in [g.str_gate_swap]:
					ctrl, trgt = inst[1:3]
					last_fidelity = get_smaller(qubit_fidelity[ctrl], qubit_fidelity[trgt])
					gate_fidelity = qchip_data["net_cnot_error"][ctrl][trgt]**3
					qubit_fidelity[ctrl] = qubit_fidelity[trgt] = last_fidelity * gate_fidelity

				elif inst[0] in [g.str_gate_measz]:
					qubit = inst[1]
					gate_fidelity = 1 - qchip_data["measure_error"]
					qubit_fidelity[qubit] *= gate_fidelity

		else:
			for inst in system_code:
				if inst[0] in [g.str_gate_cnot, g.str_gate_cz]:
					ctrl, trgt = inst[1:3]
					last_fidelity = get_smaller(qubit_fidelity[ctrl], qubit_fidelity[trgt])
					gate_fidelity = qchip_data["net_cnot_error"][ctrl][trgt]
					qubit_fidelity[ctrl] = qubit_fidelity[trgt] = last_fidelity * gate_fidelity

				elif inst[0] in [g.str_gate_swap]:
					ctrl, trgt = inst[1:3]
					last_fidelity = get_smaller(qubit_fidelity[ctrl], qubit_fidelity[trgt])
					gate_fidelity = qchip_data["net_cnot_error"][ctrl][trgt]**3
					qubit_fidelity[ctrl] = qubit_fidelity[trgt] = last_fidelity * gate_fidelity

		return min(list(qubit_fidelity.values()))
					