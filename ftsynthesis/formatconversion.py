
# -*-coding:utf-8-*-

# This code is part of ftsynthesis (fault-tolerant quantum circuit synthesis for fault-tolerant quantum protocols)
#
# Copyright 2022 ETRI
#
# This code is licensed under the BSD-3-Clause.


import collections
import re
import copy
from pprint import pprint
from icecream import ic

import globalVariable as g
import itertools
from math import *

get_bigger = lambda a, b: a if a>b else b


def cancel_redundancy(syscode):
	"""
		function to cancel out the redundant quantum gates in time order

		args:
			syscode in list
	"""

	table = collections.defaultdict(list)

	for idx, inst in enumerate(syscode):
		# 2-qubit gate : typeA (control, target 큐빗 명시가 중요한 게이트)
		if inst[0] in [g.str_gate_cnot, g.str_gate_cz]:
			if len(table[inst[1]]) and len(table[inst[2]]):
				# 새로운 명령과 이전 명령 비교
				last_instA = table[inst[1]][-1]
				last_instB = table[inst[2]][-1]

				conditionA = (last_instA["gate"] == inst[0]) and (last_instA["qubits"] == inst[1:])
				conditionB = (last_instB["gate"] == inst[0]) and (last_instB["qubits"] == inst[1:])

				# 동일하면
				if conditionA and conditionB:
					table[inst[1]].pop()
					table[inst[2]].pop()

				# 다르면
				else:
					table[inst[1]].append({"gate": inst[0], "qubits": inst[1:], "idx": idx})
					table[inst[2]].append({"gate": inst[0], "qubits": inst[1:], "idx": idx})

			else:
				table[inst[1]].append({"gate": inst[0], "qubits": inst[1:], "idx": idx})
				table[inst[2]].append({"gate": inst[0], "qubits": inst[1:], "idx": idx})

		# 2-qubit gate : typeB (control, target 큐빗 명시가 필요없는 게이트)
		elif inst[0] in [g.str_gate_swap]:
			if len(table[inst[1]]) and len(table[inst[2]]):
				# 새로운 명령과 이전 명령 비교
				last_instA = table[inst[1]][-1]
				last_instB = table[inst[2]][-1]

				conditionA = (last_instA["gate"] == inst[0]) and (set(last_instA["qubits"]) == set(inst[1:]))
				conditionB = (last_instB["gate"] == inst[0]) and (set(last_instB["qubits"]) == set(inst[1:]))

				# 동일하면
				if conditionA and conditionB:
					table[inst[1]].pop()
					table[inst[2]].pop()

				# 다르면
				else:
					table[inst[1]].append({"gate": inst[0], "qubits": inst[1:], "idx": idx})
					table[inst[2]].append({"gate": inst[0], "qubits": inst[1:], "idx": idx})

			else:
				table[inst[1]].append({"gate": inst[0], "qubits": inst[1:], "idx": idx})
				table[inst[2]].append({"gate": inst[0], "qubits": inst[1:], "idx": idx})

		# barrier-All
		elif inst[0] in [g.str_barrier_all]:
			for qubit in table.keys():
				table[qubit].append({"gate": g.str_barrier_all, "idx": idx})

		# selective barrier : 
		elif inst[0] in [g.str_barrier]:
			list_qubits = inst[1]
			for qubit in list_qubits:
				table[qubit].append({"gate": g.str_barrier, "qubits": list_qubits, "idx": idx})

		# 1-qubit gate
		elif inst[0] in [g.str_gate_rz]:
			if len(table[inst[2]]):
				last_inst = table[inst[2]][-1]

				# Rz 게이트가 연속되면, angle 확인 후, 앞선 게이트의 angle 값을 변경
				if (last_inst["gate"] == inst[0]) and (last_inst["qubits"] == inst[2:]):
					new_angle = float(eval(last_inst["angle"])) + float(eval(inst[1]))
					table[inst[2]][-1]["angle"] = str(new_angle)

				else:
					table[inst[2]].append({"gate": inst[0], "qubits": [inst[2]], "idx": idx, "angle": inst[1]})
			else:
				table[inst[2]].append({"gate": inst[0], "qubits": [inst[2]], "idx": idx, "angle": inst[1]})
		
		elif inst[0] in [g.str_gate_u]:
			if len(table[inst[2]]):
				last_inst = table[inst[2]][-1]
				if last_inst["gate"] == inst[0] and last_inst["qubits"] == inst[2:]:
					new_angle = {}
					for axis in ["x", "z", "y"]:
						new_angle[axis] = float(eval(last_inst["angle"][axis])) + float(eval(inst[1][axis]))
					table[inst[2]][-1]["angle"] = new_angle
				else:
					table[inst[2]].append({"gate": inst[0], "qubits": [inst[2]], "angle": inst[1], "idx": idx})	
			else:
				table[inst[2]].append({"gate": inst[0], "qubits": [inst[2]], "angle": inst[1], "idx": idx})

		else:
			# 새로운 명령과 이전 명령 비교
			if len(table[inst[1]]):
				last_inst = table[inst[1]][-1]

				# 동일하면
				if (last_inst["gate"] == inst[0]) and (last_inst["qubits"] == inst[1:]):
					table[inst[1]].pop()

				# 다르면
				else:
					table[inst[1]].append({"gate": inst[0], "qubits": [inst[1]], "idx": idx})	

			else:
				table[inst[1]].append({"gate": inst[0], "qubits": [inst[1]], "idx": idx})

	temp_syscode = {}
	for v_list in list(table.values()):
		for v in v_list:
			temp_syscode[v["idx"]] = v
	
	sorted_index = sorted(temp_syscode.keys())

	post_processed_syscode = []
	for k in sorted_index:
		v = temp_syscode[k]
		if v["gate"] in [g.str_gate_cnot, g.str_gate_cz, g.str_gate_swap]:
			post_processed_syscode.append([v["gate"], v["qubits"][0], v["qubits"][1]])
		
		elif v["gate"] in [g.str_gate_measz, g.str_gate_measx]:
			post_processed_syscode.append([v["gate"], v["qubits"][0], v["qubits"][0]])
		
		elif v["gate"] in [g.str_gate_rz, g.str_gate_u]:
			post_processed_syscode.append([v["gate"], v["angle"], v["qubits"][0]])

		# barrier-all
		elif v["gate"] == g.str_barrier_all:
			post_processed_syscode.append([v["gate"]])
			
		# selective barrier
		elif v["gate"] == g.str_barrier:
			post_processed_syscode.append([v["gate"], v["qubits"]])

		else:
			post_processed_syscode.append([v["gate"], v["qubits"][0]])

	return post_processed_syscode	


def transform_time_ordered_syscode(syscode, qubit_mapping):
	
	inverse_qubit_mapping = {v: k for k, v in qubit_mapping.items()}

	collections_qubits = collections.defaultdict(lambda: collections.defaultdict(bool))

	list_working_qubits = []
	circuit_index = 0

	collections_circuits = collections.defaultdict(object)
	circuit = collections.defaultdict(list)
	qubit_time_index = collections.defaultdict(int)

	for inst in syscode:
		if inst[0] in [g.str_gate_cnot, g.str_gate_cz, g.str_gate_swap]:
			ctrl, trgt = inst[1:]
			ctrl_name = inverse_qubit_mapping[ctrl]
			trgt_name = inverse_qubit_mapping[trgt]

			time_index = get_bigger(qubit_time_index[ctrl_name], qubit_time_index[trgt_name])
			circuit[time_index].append(inst)

			qubit_time_index[ctrl_name] = qubit_time_index[trgt_name] = time_index + 1

			if inst[0] == g.str_gate_swap:
				inverse_qubit_mapping[ctrl], inverse_qubit_mapping[trgt] =\
					inverse_qubit_mapping[trgt], inverse_qubit_mapping[ctrl]

		elif inst[0] in [g.str_gate_prepz, g.str_gate_prepx]:
			qubit_index = inst[1]
			qubit_name = inverse_qubit_mapping[qubit_index]

			qubit_type = qubit_name
			while qubit_type[-1].isdigit(): qubit_type = qubit_type[:-1]
			collections_qubits[qubit_type][qubit_name] = True

			circuit[qubit_time_index[qubit_name]].append(inst)
			qubit_time_index[qubit_name]+=1

		elif inst[0] in [g.str_gate_measz, g.str_gate_measx]:
			qubit_index = inst[1]
			qubit_name = inverse_qubit_mapping[qubit_index]

			qubit_type = qubit_name
			while qubit_type[-1].isdigit(): qubit_type = qubit_type[:-1]
			collections_qubits[qubit_type][qubit_name] = False

			circuit[qubit_time_index[qubit_name]].append(inst)
			qubit_time_index[qubit_name] += 1

			if not any(collections_qubits[qubit_type].values()): 
				collections_circuits[circuit_index] = circuit
				for qubit in qubit_time_index.keys(): qubit_time_index[qubit] = 0

				circuit = collections.defaultdict(list)
				circuit_index+=1
		else:
			qubit_index = inst[1]
			qubit_name = inverse_qubit_mapping[qubit_index]

			circuit[qubit_time_index[qubit_name]].append(inst)
			qubit_time_index[qubit_name]+=1

	inverse_qubit_mapping = {v: k for k, v in qubit_mapping.items()}
	for circuit_idx, circuit in collections_circuits.items():
		print(circuit_idx)
		for time_idx, instructions in circuit.items():
			for inst in instructions:
				if inst[0] in [g.str_gate_swap, g.str_gate_cnot]:
					print(inst, inst[0], inverse_qubit_mapping[inst[1]], inverse_qubit_mapping[inst[2]])

					if inst[0] == g.str_gate_swap:
						inverse_qubit_mapping[inst[1]], inverse_qubit_mapping[inst[2]] =\
							inverse_qubit_mapping[inst[2]], inverse_qubit_mapping[inst[1]]
				else:
					print(inst, inst[0], inverse_qubit_mapping[inst[1]])
		print("\n")

	pprint(collections_circuits)




def transform_ordered_syscode(syscode, number_qubits, **kwargs):
	'''
		개별 게이트의 circuit index를 분석하고, 시간순으로 정리된 회로를 생성 리턴하는 함
	'''

	if "postprocessing" in kwargs and kwargs["postprocessing"]:
		# system code 후 처리: 동일한 게이트가 연속해서 추가된 경우, 서로 cancel 시킴
		syscode = process_syscode(syscode, number_qubits)
	
	time_index = collections.defaultdict(int)
	ordered_syscode = collections.defaultdict(list)
	
	for inst in syscode:
		flag_barrier = False
		
		# ic(inst)
		if inst[0] in [g.str_gate_cnot, g.str_gate_cz, g.str_gate_swap]:
			ctrl, trgt = inst[1:]

			applying_index = max(time_index[ctrl], time_index[trgt])
			time_index[ctrl] = time_index[trgt] = applying_index+1
			list_command = "{} {},{}".format(inst[0], ctrl, trgt)
		
		elif inst[0] in ["Qubit", "Cbit"]: continue
			
		else: 
			if inst[0] in [g.str_gate_rz, g.str_gate_rx, g.str_gate_ry, g.str_gate_phase]:
				angle, qubit = inst[1:]
				list_command = "{}({}) {}".format(inst[0], angle, qubit)
				applying_index = time_index[qubit]
				time_index[qubit] += 1
			
			elif inst[0] in [g.str_gate_u]:
				*angle, qubit = inst[1:]
				list_command = "{}({},{},{}) {}".format(inst[0], angle[0], angle[1], angle[2], qubit)
				applying_index = time_index[qubit]
				time_index[qubit] += 1
			
			elif inst[0] in [g.str_gate_measz, g.str_gate_measx]:
				qubit, cbit, *arguments = inst[1:]
				list_str_command = [inst[0], str(qubit), "->", str(cbit)]
				
				if len(arguments):
					sub_args_command = []
					# for value in arguments:
					# 	if isinstance(value, int):
					# 		sub_args_command.append("expected={}".format(str(value)))
					# 	# if value.isdigit():
					# 	# 	sub_args_command.append("expected={}".format(str(value)))
					# 	else:
					# 		sub_args_command.append("role={}".format(value))

					str_args = ",".join(sub_args_command)
					str_args = "(" + str_args + ")"
					list_str_command.append(str_args)

				list_command = " ".join(list_str_command)

				applying_index = time_index[qubit]
				time_index[qubit] += 1
			

			elif inst[0] in ["Qubit"]:
				if len(inst[1:]) == 2:
					qubit, size = inst[1:]
					list_command = "{} {} {}".format(inst[0], qubit, size)
				else:
					qubit = inst[1]
					list_command = "{} {}".format(inst[0], qubit)

			
			elif inst[0] == g.str_barrier_all:
				flag_barrier = True
				list_command = g.str_barrier_all
				applying_index = max(list(time_index.values()))

				for qubit in time_index.keys():
					time_index[qubit] = applying_index

			elif inst[0] == g.str_barrier:
				flag_barrier = True
				list_command = "{} {}".format(g.str_barrier, inst[1])
				applying_index = max(time_index[qubit] for qubit in inst[1])

				for qubit in inst[1]: time_index[qubit] = applying_index

			else:
				qubit = inst[1]
				list_command = "{} {}".format(inst[0], qubit)
				applying_index = time_index[qubit]
				time_index[qubit] += 1
				
			
		if flag_barrier: applying_index -= 1

		ordered_syscode[applying_index].append(list_command)

	return ordered_syscode



def extract_list_qubits(syscode):
	list_qubits = []
	parser = re.compile("[\{a-zA-Z0-9_.*/\->\+}]+")

	if type(syscode) in [collections.defaultdict, dict]:
		for time_index, list_instrunctions in syscode.items():
			for instruction in list_instrunctions:
				token = parser.findall(instruction)
				if not len(token): continue

				if token[0] in ["CNOT", "cx", "cz"]: list_qubits.extend(map(int, token[1:3]))
				else:
					if token[0] in ["Rz", "rz", "Rx", "rx", "Ry", "ry", "P"]:
						angle, qubit = token[1:]
						list_qubits.append(int(qubit))
					
					elif token[0] in ["U"]:
						_, _, _, qubit = token[1:]
						list_qubits.append(int(qubit))
					
					elif token[0] not in ["Cbit"]:
						list_qubits.append(int(token[1]))

	return set(list_qubits)




def transform_to_openqasm(qasm, **kwargs):
	if "number_qubits" in kwargs:
		number_qubits = kwargs["number_qubits"]

	list_converted_code = []
	list_converted_code.append(["OPENQASM 2.0"])
	list_converted_code.append(["include \"qelib1.inc\""])

	list_converted_code.append(["qreg", "{}".format(number_qubits)])
	list_converted_code.append(["creg", "{}".format(number_qubits)])

	flag_measurement_appear = False

	for inst in qasm:
		if inst[0] in ["PrepZ"]: 
			list_converted_code.append(["reset", "{}".format(inst[1])])

		elif inst[0] in ["X", "Z", "Y", "I", "H", "SX", "S"]:
			list_converted_code.append(["{}".format(inst[0].lower()), "{}".format(inst[1])])

		elif inst[0] in ["CNOT", "cx"]:
			list_converted_code.append(["cx", "{}".format(inst[1]), "{}".format(inst[2])])

		elif inst[0] in ["MeasZ"]:
			list_converted_code.append(["measure", "{}".format(inst[1]), "{}".format(inst[3])])

		elif inst[0] in ["Rx", "Rz", "Ry", "P"]:
			list_converted_code.append(["{}".format(inst[0].lower()), "{}".format(inst[1]), "{}".format(inst[2])])

		elif inst[0] in ["U"]:
			inst[0] = inst[0].lower()
			list_converted_code.append(inst)

	return list_converted_code


def preanalyze_qasm(qasm):
	'''
		commutable cnot swap 함수
		args: qasm in list data structure
	'''
	import re
	p = re.compile("[\{a-zA-Z0-9_.*\->\}]+")

	idx = 0

	# list_qasm -> idx: qasm instruction
	list_qasm = {}

	# monitoring_CNOT -> [{"control": ..., "target": ..., "idx": idx}, {..}]
	list_monitoring_CNOT = []

	# qubit -> qubit : [{"qubit": .., "cnots": [.. ]}]
	list_monitoring_qubit = []

	list_memory_declaration = []
	# with open(file_qasm, "r") as infile:
	
	for command in qasm:
		# 일단 순서대로 list에 저장
		list_qasm[idx] = command

		if command[0] in ["Qubit", "Cbit"]: 
			idx += 1
			continue

		# 게이트 타입에 따라 연산 작업
		# case 1: CNOT
		if command[0] == "CNOT":
			ctrl, trgt = command[1:]
			if ctrl == trgt:
				raise Exception("For CNOT, ctrl qubit and trgt qubit are the same. {}".format(command))

			# 새로운 CNOT의 ctrl, trgt 큐빗이 기존 CNOT에 물려 있는지 확인
			# check 1: ctrl 만 공유되는 상황 
			# check 2: ctrl 과 trgt 가 공유되는 상황
			# check 3: check 1과 2는 아니지만, 어떻게는 큐빗 공유는 이루어지는 상황
			# check 4: 새로운 cnot 과 앞선 cnot 들이 완전히 독립적인 상황

			flag_checking = {k: False for k in range(3)}
			flag_new = True
			for cnot in list_monitoring_CNOT:
				if ctrl == cnot["control"]:
					if trgt == cnot["target"]:
						print("기존 CNOT: {}, 신규 CNOT : {}".format(cnot, (ctrl, trgt)))
						print("중복 발생")
						list_monitoring_CNOT.remove(cnot)
						# list_monitoring_CNOT.append({"control": ctrl, "target": trgt, "id": idx})
						flag_new = False
					
					else:
						print("기존 CNOT: {}, 신규 CNOT : {}".format(cnot, (ctrl, trgt)))
						print("교환 대상")
						list_monitoring_CNOT.append({"control": ctrl, "target": trgt, "id": idx})
						list_monitoring_qubit.append({"qubit": trgt, 
													  "cnot_list": [cnot, {"control": ctrl, "target": trgt, "id": idx}]})
						flag_new = False

				else:
					if ctrl == cnot["target"] or trgt in list(cnot.values()):
						print("기존 CNOT: {}, 신규 CNOT : {}".format(cnot, (ctrl, trgt)))
						print("기존 CNOT 제거 & 신규 CNOT 추가")
						list_monitoring_CNOT.remove(cnot)
						list_monitoring_CNOT.append({"control": ctrl, "target": trgt, "id": idx})
						flag_new = False
				break

			if flag_new:
				print("독립적인 CNOT 게이트")
				list_monitoring_CNOT.append({"control": ctrl, "target": trgt, "id": idx})

			print("list of monitoring cnot: ")
			pprint(list_monitoring_CNOT)

		# case 2: one-qubit gate
		else:
			# case 2-1: rotational gate with arguments: angle and qubit
			if command[0] in ["Rz", "rz"]: qubit = command[2]
			# case 2-2: the other one-qubit gate with argument: qubit
			else: qubit = command[1]

			if not len(list_monitoring_qubit):
				for cnot in list_monitoring_CNOT:
					if cnot["control"] == qubit or cnot["target"] == qubit:
						list_monitoring_CNOT.remove(cnot)

			pprint(list_monitoring_qubit)
			for q in list_monitoring_qubit:
				# check 1: 공통 control 큐빗에 one-qubit 게이트가 인가된 경우
				if (q["cnot_list"][0]["control"] == qubit) and (q["cnot_list"][1]["control"] == qubit):
					print("case 1-1.. ")
					former, latter = q["cnot_list"][:]
					list_monitoring_CNOT.remove(former)
					list_monitoring_CNOT.remove(latter)
					list_monitoring_qubit.remove(q)

				# # check 2: 첫번째 cnot의 타겟 큐빗에 one-qubit 게이트가 인가된 경우
				# if q["cnot_list"][0]["target"] == qubit:
				# 	pprint(q["cnot_list"])
				# 	former, latter = q["cnot_list"][:]
				# 	list_monitoring_CNOT.remove(former)
				# 	list_monitoring_qubit.remove(q)
				# check 3
				if q["qubit"] == qubit:
					print("교환하자... {}".format(q["cnot_list"]))
					print("교환 이전: ")
					pprint(list_qasm)
					former, latter = q["cnot_list"][:]
					list_qasm[former["id"]] = ["CNOT", latter["control"], latter["target"]]
					list_qasm[latter["id"]] = ["CNOT", former["control"], former["target"]]
					
					print("교환 결과: ")
					pprint(list_qasm)
					# list_monitoring_CNOT.remove(former)
					list_monitoring_CNOT.remove(latter)
					list_monitoring_qubit.remove(q)

					print("monitoring cnot: ")
					pprint(list_monitoring_CNOT)
					print("monitoring qubit: ")
					pprint(list_monitoring_qubit)

		idx += 1

	return list(list_qasm.values())


def preanalyze_qasm_file(file_qasm):
	'''
		commutable cnot swap 함수
		args: qasm in file
	'''

	import re
	p = re.compile("[\{a-zA-Z0-9_.*\->\}]+")

	idx = 0

	# list_qasm -> idx: qasm instruction
	list_qasm = {}

	# monitoring_CNOT -> [{"control": ..., "target": ..., "idx": idx}, {..}]
	list_monitoring_CNOT = []

	# qubit -> qubit : [{"qubit": .., "cnots": [.. ]}]
	list_monitoring_qubit = []

	list_memory_declaration = []
	with open(file_qasm, "r") as infile:
		for line in infile:
			tokens = p.findall(line)
			# print(tokens)
			if not len(tokens):  continue

			# 일단 순서대로 list에 저장
			list_qasm[idx] = tokens

			if tokens[0] in ["Qubit", "Cbit"]: 
				idx += 1
				continue

			# 게이트 타입에 따라 연산 작업
			# case 1: CNOT
			if tokens[0] == "CNOT":
				ctrl, trgt = tokens[1:]
				if ctrl == trgt:
					raise Exception("For CNOT, ctrl qubit and trgt qubit are the same. {}".format(tokens))
				# 새로운 CNOT의 ctrl, trgt 큐빗이 기존 CNOT에 물려 있는지 확인
				# check 1: ctrl 만 공유되는 상황 
				# check 2: ctrl 과 trgt 가 공유되는 상황
				# check 3: check 1과 2는 아니지만, 어떻게는 큐빗 공유는 이루어지는 상황
				# check 4: 새로운 cnot 과 앞선 cnot 들이 완전히 독립적인 상황

				flag_checking = {k: False for k in range(3)}
				flag_new = True
				for cnot in list_monitoring_CNOT:
					if ctrl == cnot["control"]:
						if trgt == cnot["target"]:
							print("기존 CNOT: {}, 신규 CNOT : {}".format(cnot, (ctrl, trgt)))
							print("중복 발생")
							list_monitoring_CNOT.remove(cnot)
							# list_monitoring_CNOT.append({"control": ctrl, "target": trgt, "id": idx})
							flag_new = False
						
						else:
							print("기존 CNOT: {}, 신규 CNOT : {}".format(cnot, (ctrl, trgt)))
							print("교환 대상")
							list_monitoring_CNOT.append({"control": ctrl, "target": trgt, "id": idx})
							list_monitoring_qubit.append({"qubit": trgt, 
														  "cnot_list": [cnot, {"control": ctrl, "target": trgt, "id": idx}]})
							flag_new = False

					else:
						if ctrl == cnot["target"] or trgt in list(cnot.values()):
							print("기존 CNOT: {}, 신규 CNOT : {}".format(cnot, (ctrl, trgt)))
							print("기존 CNOT 제거 & 신규 CNOT 추가")
							list_monitoring_CNOT.remove(cnot)
							list_monitoring_CNOT.append({"control": ctrl, "target": trgt, "id": idx})
							flag_new = False
					break

				if flag_new:
					print("독립적인 CNOT 게이트")
					list_monitoring_CNOT.append({"control": ctrl, "target": trgt, "id": idx})

				print("list of monitoring cnot: ")
				pprint(list_monitoring_CNOT)

			# case 2: one-qubit gate
			else:
				# case 2-1: rotational gate with arguments: angle and qubit
				if tokens[0] in ["Rz", "rz"]: qubit = tokens[2]
				# case 2-2: the other one-qubit gate with argument: qubit
				else: qubit = tokens[1]

				if not len(list_monitoring_qubit):
					for cnot in list_monitoring_CNOT:
						if cnot["control"] == qubit or cnot["target"] == qubit:
							list_monitoring_CNOT.remove(cnot)

				for q in list_monitoring_qubit:
					# check 1: 공통 control 큐빗에 one-qubit 게이트가 인가된 경우
					if (q["cnot_list"][0]["control"] == qubit) and (q["cnot_list"][1]["control"] == qubit):
						print("case 1-1.. ")
						former, latter = q["cnot_list"][:]
						list_monitoring_CNOT.remove(former)
						list_monitoring_CNOT.remove(latter)
						list_monitoring_qubit.remove(q)

					# # check 2: 첫번째 cnot의 타겟 큐빗에 one-qubit 게이트가 인가된 경우
					# if q["cnot_list"][0]["target"] == qubit:
					# 	pprint(q["cnot_list"])
					# 	former, latter = q["cnot_list"][:]
					# 	list_monitoring_CNOT.remove(former)
					# 	list_monitoring_qubit.remove(q)
					# check 3
					if q["qubit"] == qubit:
						print("교환하자... {}".format(q["cnot_list"]))
						print("교환 이전: ")
						pprint(list_qasm)
						former, latter = q["cnot_list"][:]
						list_qasm[former["id"]] = ["CNOT", latter["control"], latter["target"]]
						list_qasm[latter["id"]] = ["CNOT", former["control"], former["target"]]
						
						print("교환 결과: ")
						pprint(list_qasm)
						# list_monitoring_CNOT.remove(former)
						list_monitoring_CNOT.remove(latter)
						list_monitoring_qubit.remove(q)

						print("monitoring cnot: ")
						pprint(list_monitoring_CNOT)
						print("monitoring qubit: ")
						pprint(list_monitoring_qubit)

			idx += 1

	with open(file_qasm, "w") as outfile:
		for idx, inst in list_qasm.items():
			if inst[0] in ["Qubit", "Cbit"]:
				str_command = "{} {}\n".format(inst[0], inst[1])

			elif inst[0] == "CNOT":
				str_command = "{} {},{}\n".format(inst[0], inst[1], inst[2])
			
			elif inst[0] in ["Rz", "rz"]: 
				str_command = "{}({}) {}\n".format(inst[0], inst[1], inst[2])
			
			elif inst[0] in ["MeasZ"]:
				str_command = "{} {} -> {}\n".format(inst[0], inst[1], inst[3])	
			
			else:
				str_command = "{} {}\n".format(inst[0], inst[1])

			outfile.write(str_command)

	return file_qasm
