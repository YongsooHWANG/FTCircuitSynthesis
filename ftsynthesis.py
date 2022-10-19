# -*-coding:utf-8-*-

"""
	quantum circuit synthesizer for fault-tolerant quantum computing protocol
	single process version
"""

# python standard library
import os
import re

import simplejson as json
import collections
import numpy as np
import math
import copy
import multiprocessing
from datetime import datetime

from icecream import ic
from progress.bar import Bar
import parse

# package for picking a random qubit mapping (developed by YH)
import qubitmapping

import DirectedAcyclicGraph
import DistanceMatrix as DM
import SABRE_utility
import util
import globalVariable as g
import checkup
import formatconversion

import depth_analysis

decay = 0

extended_set_weight = 0
g.initialize_globals()

# default value of the lap_depth -> 0
lap_depth = 0

# constant for qubit's usage status
flag_active = "active"
flag_inactive = "inactive"


def calculate_NNC_cost(FL, DM, MT, **kwargs):
	'''
		cost function based on nearest neighbor cost
		simply sum the distance between qubits over FL
	'''

	temp_sum = 0
	for node in FL:
		if node["gate"] in [g.str_gate_cnot, g.str_gate_cz]:
			temp_sum += DM[MT[node["ctrl"]]][MT[node["trgt"]]]

		elif node["gate"] in [g.str_move]: 
			temp_sum += DM[MT[node["ctrl"]]][node["trgt"]]
		
	return temp_sum	


def calculate_LAP_cost(SWAP, DAG, FL, DM, MT, listDecay, position_data_qubits={}):
	'''
		cost function based on Look-Ahead Ability and Parallelism
	'''
	
	temp_cost_F = 0
	temp_cost_E = 0

	decay = max(listDecay[SWAP[0]], listDecay[SWAP[1]])
	extended_set = []
	
	# sum the distance for the front layer
	for node in FL:
		if node["gate"] in [g.str_gate_cnot, g.str_gate_cz, g.str_gate_swap]:
			associated_physical_ctrl_qubit = MT[node["ctrl"]]
			associated_physical_trgt_qubit = MT[node["trgt"]]

		elif node["gate"] == g.str_move:
			associated_physical_ctrl_qubit = MT[node["ctrl"]]
			associated_physical_trgt_qubit = node["trgt"]
		
		elif node["gate"] in [g.str_barrier, g.str_barrier_all]: continue

		temp_cost_F += DM[associated_physical_ctrl_qubit][associated_physical_trgt_qubit]
		
		# function to get an extended groups based on the current node 			
		# gathering the extended set ahead of the FL
		extended_set.extend(DirectedAcyclicGraph.get_children_from_node(DAG, node, lap_depth))

	# sum the distance in the extended set
	for node in extended_set:
		if DAG.nodes[node]["gate"] in [g.str_gate_cnot, g.str_gate_cz, g.str_gate_swap]:
			associated_physical_ctrl_qubit = MT[DAG.nodes[node]["ctrl"]]
			associated_physical_trgt_qubit = MT[DAG.nodes[node]["trgt"]]
			
		elif DAG.nodes[node]["gate"] == g.str_move:
			associated_physical_ctrl_qubit = MT[DAG.nodes[node]["ctrl"]]
			associated_physical_trgt_qubit = DAG.nodes[node]["trgt"]

		elif DAG.nodes[node]["gate"] in [g.str_barrier, g.str_barrier_all]: continue

		temp_cost_E += DM[associated_physical_ctrl_qubit][associated_physical_trgt_qubit]

	# calculating the cost
	cost = float(temp_cost_F/len(FL))
	if len(extended_set):
		cost += extended_set_weight * float(temp_cost_E/len(extended_set))
	cost *= decay

	return cost


def SABRE(DAG, FL, MT, DistanceMatrix, qchip_data, **kwargs):
	'''

		graph traversal part
		args:
			DM: distance matrix from qubit connectivity
			DAG: directed acyclic graph from algorithm
			FL: front layer from DAG
			MT: random qubit mapping table
	'''

	# reset the seed for random number for every traversal to keep the random
	np.random.seed(datetime.now().microsecond%10)

	list_syscode_commands = []
	
	# user's selection for cost function (default : nnc)
	cost_function = kwargs.get("cost")
	if cost_function is None: cost_function = "nnc"

	# user's selection to write circuit (default : no)
	flag_write_syscode = kwargs.get("write_syscode")
	if flag_write_syscode is None: flag_write_syscode = False

	# user's selection for allowing swap (default : no)
	flag_swap = kwargs.get("allow_swap")
	if flag_swap is None: flag_swap = False

	# position of data qubits
	position_data_qubits = kwargs.get("position_data_qubits")

	# direction of current SABRE round
	SABRE_direction = kwargs.get("direction")
	
	# the upper bound for allowing the interaction between data qubits (default: 0)
	number_allowable_data_interaction = kwargs.get("allowable_data_interaction")
	if number_allowable_data_interaction is not None:
		number_allowable_data_interaction = int(number_allowable_data_interaction)
	else:
		number_allowable_data_interaction = 0

	# type of the qubits employed in the protocol
	qubit_info = kwargs.get("qubit_info")

	# initialization of qubits' usage status according to the qubits
	# qubit status change: "inactive" -> "active" by prepare
	#                      "active" -> "inactive" by measure 
	
	# the data qubits and the magic qubits are so-called data qubits of a logic qubit (magic state)
	# therefore, the status of each should be active from the beginning
	table_qubit_status = {}
	for active_qubit in ["data", "magic"]:
		if active_qubit not in qubit_info.keys(): continue
		table_qubit_status.update({qubit : flag_active for qubit in qubit_info[active_qubit]})
	
	# for other type of qubits such as ancilla, we set its initial usage status as inactive
	for k in list(MT.keys()):
		if all(label not in k for label in ["data", "magic"]):
			table_qubit_status.update({k: flag_inactive})

	# inverse of qubit mapping 
	inverse_MT = {v: k for k, v in MT.items()}
	# list of decay 
	listDecay = collections.defaultdict(lambda: 0)
	# list of qubits moved back to home
	list_qubits_moved_back = []

	# list of qubits should be moved back to home 
	list_for_moveback = []
	# list for gates delayed by barrier
	list_for_barrier = collections.defaultdict(list)

	# for the forward graph traversal, the moveback should be conducted
	# for the moveback, ctrl qubit is needed to go to the trgt position
	table_moveback = {}

	# for move operation, translat the destination written symbolically to the specific qubit location
	if SABRE_direction == "forward":
		for i in DAG.nodes:
			if DAG.nodes[i]["gate"] in [g.str_move]:
				# if the trgt is provided symbolically as (-init),
				# it is translated to a physical specific index
				if type(DAG.nodes[i]["trgt"]) == str and "init" in DAG.nodes[i]["trgt"]:
					result = parse.compile("{}-init").parse(DAG.nodes[i]["trgt"])
					if result is None:
						DAG.nodes[i]["trgt"] = position_data_qubits[DAG.nodes[i]["trgt"]]
					else:
						DAG.nodes[i]["trgt"] = position_data_qubits[result[0]]

				table_moveback[DAG.nodes[i]["ctrl"]] = DAG.nodes[i]

		# for fl_node in FL:
		# 	if fl_node["gate"] in [g.str_move]:
		# 		if type(fl_node["trgt"]) == str and "init" in fl_node["trgt"]:
		# 			result = parse.compile("{}-init").parse(fl_node["trgt"])
		# 			if result is None:
		# 				fl_node["trgt"] = position_data_qubits[fl_node["ctrl"]]
		# 			else:
		# 				fl_node["trgt"] = position_data_qubits[result[0]]

		# 		table_moveback[fl_node["ctrl"]] = fl_node
	
	flag_moveback = False

	# counter to count the interaction (SWAP gate) between data qubits
	count_data_interaction = 0

	# variable of the optimal swap chosen in the previous iteration
	previous_best_SWAP = None

	interactions = collections.defaultdict(int)
	# list_ready_instructions = collections.defaultdict(object)
	list_executed_nodes = set([])

	while len(FL):
		list_executable_gates = []
		# 1. checking the executability of a quantum gate in the front layer
		# 	 if yes, it is added to list_executable_gates

		# check the executablity of a quantum gate in terms of the qubit connectivity
		# find executable gates
		# the main focus : 2-qubit gate, move, barrier
		for node in FL:
			if node["gate"] in g.list_one_qubit_gates:
				list_executable_gates.append(node)

			elif node["gate"] in ["Qubit"]:
				list_executable_gates.append(node)

			# two-qubit gate
			elif node["gate"] in [g.str_gate_cnot, g.str_gate_cz, g.str_gate_swap]:
				ctrl_qubit = node["ctrl"]
				trgt_qubit = node["trgt"]

				# in case of the 2-qubit gate, 
				# if the qubits ctrl and trgt is located in neighbor, it is executable
				if MT[trgt_qubit] in qchip_data["qubit_connectivity"][MT[ctrl_qubit]]:
					list_executable_gates.append(node)

			# move
			elif node["gate"] == g.str_move:
				ctrl_qubit = node["ctrl"]
				flag_moveback = True

				# for a move, the qubit (set as ctrl) should be placed in the destination (set as trgt)
				if MT[ctrl_qubit] == node["trgt"]: 
					list_executable_gates.append(node)
					list_qubits_moved_back.append(ctrl_qubit)

			# barrier for all qubits (in the paper)
			# if the remaining nodes in FL are barrier all (actually only one node in FL)
			elif node["gate"] == g.str_barrier_all:
				if all(node["gate"] == g.str_barrier_all for node in FL):
					list_executable_gates.append(node)

			# in the upgraded algorithm, we treat a selective barrier (blocking subset of qubits not all)
			# therefore tested enough not yet..

			# selective barrier 가 실행 가능한 경우: 
			# "barrier a,b,c" 경우, FL 내부에 큐빗 a, b, c 에 동작하는 명령이 없는 경우 가능함
			# 먼저, 0) FL 내 나 혼자 남았으면, 실행 가능
			# 따라서, 1) barrier 에서 locked 큐빗을 확인하고, 2) FL 내 모든 노드(양자명령)이 동작하는 큐빗 목록을 확인함
			# 만약, 3) 두 노드 셋이 교집합이 empty이면, 해당 barrier 실행 가능함
			elif node["gate"] == g.str_barrier: continue
				
		# 2. if list_executable_gates is not empty, 
		#	1) delete a gate from front layer
		# 	2) see succeeding gates at DAG
		#	3) by checking the logical dependency, pull it into FL if the dependency is resolved
		#		# how to check the dependency
		#		(1)	check the preceding gates of a gate reside in FL
		#		(2) if yes, it is not the turn to consider for the gate to execute
		#		(3) otherwise, it can be pulled into FL 

		# if list_executable_gates is not empty, we need to treat it properly
		# 	1) delete a gate in the list from FL
		# 	2) find a succeeding gate in DAG, but it's logical dependency is free (that is all of its preceding gates are not remained in FL of DAG) and
		# 	   pull it to FL
		if len(list_executable_gates):
			for node in list_executable_gates:

				# update status of ancilla qubits (syndrome, syndrome verification qubits)
				# in the forward traversal, by preparation it becomes as activated and by measurement it becomes as inactivated
				# in the backward traversal, by measurement it becomes as activated and by preparation it becomes as inactivated
				if node["gate"] in [g.str_gate_prepz, g.str_gate_prepx]:
					if SABRE_direction == "forward":
						table_qubit_status[node["trgt"]] = flag_active

					elif SABRE_direction == "backward":
						table_qubit_status[node["trgt"]] = flag_inactive

				elif node["gate"] in [g.str_gate_measz, g.str_gate_measx]:
					if SABRE_direction == "forward":
						table_qubit_status[node["trgt"]] = flag_inactive
				
					elif SABRE_direction == "backward":
						table_qubit_status[node["trgt"]] = flag_active

				# By running a "barrier" statement, we move the elements held in the list_for_barrier to FL
				# As mentioned above, the list list_for_barrier keeps the quantum gates should be executed after the barrier statement forcibly
				elif node["gate"] == g.str_barrier_all:
					list_instructions = list_for_barrier.get("all")
					
					if list_instructions is not None:
						FL.extend(list_instructions)
						list_for_barrier["all"] = []

				# in the upgraded algorithm, we will deal with a selective barrier 
				# the following part deals with it, but not tested enough
				elif node["gate"] == g.str_barrier: continue
					
				# flag writing a circuit on a text file
				# according to the quantum gate, the format is little different

				if flag_write_syscode:
					if node["gate"] in g.list_one_qubit_gates:
						# measurement
						if node["gate"] in [g.str_gate_measz, g.str_gate_measx]:
							# in case where the classical bit is not provided
							try:
								list_command = [node["gate"], MT[node["trgt"]], node["cbit"]]
							except:
								list_command = [node["gate"], MT[node["trgt"]]]

							list_syscode_commands.append(list_command)
							
						# rotational gate
						elif node["gate"] in [g.str_gate_rz]:
							list_syscode_commands.append([node["gate"], node["angle"], MT[node["trgt"]]])
							
						# other H, Pauli, T, Tdag gates
						else:
							list_syscode_commands.append([node["gate"], MT[node["trgt"]]])

					# two qubit gates
					elif node["gate"] in [g.str_gate_cnot, g.str_gate_swap, g.str_gate_cz]:
						list_syscode_commands.append([node["gate"], MT[node["ctrl"]], MT[node["trgt"]]])

					# barrier : need to display barrier-all to partition the circuit
					elif node["gate"] == g.str_barrier_all:
						list_syscode_commands.append([node["gate"]])

					# selective barrier statement to block a subset of all qubits
					elif node["gate"] == g.str_barrier: continue
				
				# delete a gate that is executable 
				FL.remove(node)
				# add the executagle gate to the list list_executed_node to check the logical dependency later
				list_executed_nodes.add(node["id"])
				
				# to check the succeeding nodes with respect to the current executable node
				# for succeeding nodes with respect to the current executable node
				for j in DAG.successors(node["id"]):
					# nodes in FL
					list_FL_nodes = set([fl_node["id"] for fl_node in FL])
					
					# for the preceding nodes from the node j
					ancestors = set(DAG.predecessors(j))

					# investigate all the preceding nodes of j are executable
					# if yes, j can be pulled to FL with the following instructions

					# all preceding nodes are already executed, then for succeeding nodes
					if ancestors.issubset(list_executed_nodes):
						
						# if the succeeding gate is move, then it is kept in list_for_moveback
						# not for FL 						
						if DAG.nodes[j]["gate"] == g.str_move:
							list_for_moveback.append(DAG.nodes[j])

						else:
							# if the barrier statement is in FL, the following instruction is appened in the list 
							# list_for_barrier not FL

							if g.str_barrier_all in [temp_node["gate"] for temp_node in FL]:
								list_for_barrier["all"].append(DAG.nodes[j])

							# 후속 노드가 barrier 이면, 
							# 해당 barrier 에 의해 대기가 걸리는 큐빗에 동작하는 연산 노드가 FL 에 없으면, FL 에 추가 가능
							elif DAG.nodes[j]["gate"] == g.str_barrier: continue
	

							# 현재 FL 에 selective barrier 가 포함되어 있고, 
							# j의 대상 큐빗이 해당 barrier 에 의해 locked 큐빗에 속하면 list_for_barrier[key] 에 포함, 
							# 아니며, FL 에 포함
							elif g.str_barrier in [temp_node["gate"] for temp_node in FL]: 
								continue

							else:
								# 삭제된 양자 명령의 후속이 일반 양자 게이트이면, FL 에 추가
								FL.append(DAG.nodes[j])

		# 3. if list_executable_gates is empty : collect swap candidates
		#	1) initialize the data structure "score"
		#	2) appending swap gates into the list "SWAP_candidate_list" 
		#		- the candidates : inactivated qubits, activate qubit and inactivated qubit, activated qubits under control
		#		- 					the neighbor qubits (not both activated qubits) of both the activated qubits
		#	3) for swap candidate gates, evaluate the cost (nnc or lap)
		#	4) pick an optimal (minimal cost) one
		#	5) update the qubit mapping based on the chosen one
		else:
			# function to obtain swap candidate gates working fault tolerantly
			SWAP_candidate_list = []
			# pass the barrier statement
			# for forward direction: include moveback 
			# for backward direction: not include moveback
			for node in FL:
				if node["gate"] in [g.str_barrier_all, g.str_barrier]: continue
				if SABRE_direction == "backward" and node["gate"] == g.str_move: continue

				# for 2-qubit gates (CNOT, CZ, SWAP, CX etc.), swap based on both the ctrl and trgt qubits
				# for move, swap based on both the ctrl is included.
				#           in case of trgt, it is limitedly included
				if node["gate"] in [g.str_gate_cnot, g.str_gate_swap, g.str_gate_cz]:
					ctrl_qubit = node["ctrl"]
					trgt_qubit = node["trgt"]

					associated_physical_ctrl_qubit = MT[ctrl_qubit]
					associated_physical_trgt_qubit = MT[trgt_qubit]

				elif node["gate"] == g.str_move:
					ctrl_qubit = node["ctrl"]
					trgt_qubit = node["trgt"]

					associated_physical_ctrl_qubit = MT[ctrl_qubit]
					associated_physical_trgt_qubit = trgt_qubit

				# in case of inactive qubit, it can be used as a communication channel
				if table_qubit_status[ctrl_qubit] != flag_active:
					temp_swaps = [(ctrl_qubit, inverse_MT[j])
									for j in qchip_data["qubit_connectivity"][associated_physical_ctrl_qubit]]

					SWAP_candidate_list.extend(temp_swaps)

				# the active data qubit, 
				# swap can be included based on the status of its neighbor qubits
				else:
					for j in qchip_data["qubit_connectivity"][associated_physical_ctrl_qubit]:
						# if neighbor is inactive status, swap is included
						if table_qubit_status.get(inverse_MT[j]) != flag_active:
							SWAP_candidate_list.append((ctrl_qubit, inverse_MT[j]))
													
						# if neighbor is in activated, then
						else:
							# condition 1: swap is possible based on the predefined the bound for the interaction between activated qubits 
							# if the current counter < bound
							if count_data_interaction < number_allowable_data_interaction:
								SWAP_candidate_list.append((ctrl_qubit, inverse_MT[j]))

							# condition 2: neighbor and its neighbor (2nd level)
							temp_swaps = [(inverse_MT[j], inverse_MT[neighbor])
											for neighbor in qchip_data["qubit_connectivity"][j] 
											if table_qubit_status.get(inverse_MT[neighbor]) != flag_active]

							SWAP_candidate_list.extend(temp_swaps)
				
				# for target qubit
				if node["gate"] not in [g.str_move]:
					# if trgt is inactivated, it can be used as a communication channel
					if table_qubit_status.get(trgt_qubit) != flag_active:
						temp_swaps = [(trgt_qubit, inverse_MT[j]) 
										for j in qchip_data["qubit_connectivity"][associated_physical_trgt_qubit]]
						
						SWAP_candidate_list.extend(temp_swaps)

					# if trgt data qubit in activated status, then the swap is possible based on the status of its neighbor qubit
					else:
						for j in qchip_data["qubit_connectivity"][associated_physical_trgt_qubit]:
							
							# if neighbor is inactivated, swap is included
							if table_qubit_status.get(inverse_MT[j]) != flag_active:
								SWAP_candidate_list.append((trgt_qubit, inverse_MT[j]))

							# if neighbor is in activated, then
							else:
								# condition 1: swap is possible based on the predefined the bound for the interaction between activated qubits 
								# if the current counter < bound
								if count_data_interaction < number_allowable_data_interaction:
									SWAP_candidate_list.append((trgt_qubit, inverse_MT[j]))

								# condition 2: neighbor and its neighbor (2nd level)
								temp_swaps = [(inverse_MT[j], inverse_MT[neighbor])
												for neighbor in qchip_data["qubit_connectivity"][j] 
												if table_qubit_status.get(inverse_MT[neighbor]) != flag_active]

								SWAP_candidate_list.extend(temp_swaps)
				
				# for move, it the quantum state stays at trgt is ancilla (not data and magic),
				# it is possible to perform a swap based on the qubit
				else:
					if "data" not in inverse_MT[trgt_qubit] and "magic" not in inverse_MT[trgt_qubit]:
						temp_swaps = [(inverse_MT[trgt_qubit], inverse_MT[j]) 
										for j in qchip_data["qubit_connectivity"][trgt_qubit] 
										if table_qubit_status.get(inverse_MT[j]) != flag_active]

						SWAP_candidate_list.extend(temp_swaps)

				# checkup if swap acting on both activated qubits is included
				for swap in SWAP_candidate_list:
					if all("dummy" in qubit for qubit in [swap[0], swap[1]]):
						del swap
						continue

					if MT[swap[0]] not in qchip_data["qubit_connectivity"][MT[swap[1]]]:
						print(swap, MT[swap[0]], MT[swap[1]], qchip_data["qubit_connectivity"])
						raise Exception("error happend. they are not adjacent. {}".format(swap))
					
					if count_data_interaction > number_allowable_data_interaction:
						if any ("dummy" not in qubit for qubit in [swap[0], swap[1]]):
							raise Exception("error happend. both qubits are data type. {}".format(swap))

			# evaluating the swap candidate gates
			if len(SWAP_candidate_list):
				cost = {}
				
				# cost function : lap
				if cost_function == "lap":
					decay_factor = 1 + decay
					for SWAP in SWAP_candidate_list:
						MT[SWAP[0]], MT[SWAP[1]] = MT[SWAP[1]], MT[SWAP[0]]
						listDecay[SWAP[0]] += decay_factor
						listDecay[SWAP[1]] += decay_factor

						cost[SWAP] = calculate_LAP_cost(SWAP, DAG, FL, DistanceMatrix, MT, listDecay)
						
						listDecay[SWAP[0]] -= decay_factor
						listDecay[SWAP[1]] -= decay_factor
						MT[SWAP[0]], MT[SWAP[1]] = MT[SWAP[1]], MT[SWAP[0]]
				
				# cost function : nnc
				elif cost_function == "nnc":
					for SWAP in SWAP_candidate_list:
						MT[SWAP[0]], MT[SWAP[1]] = MT[SWAP[1]], MT[SWAP[0]]
						cost[SWAP] = calculate_NNC_cost(FL, DistanceMatrix, MT)
						MT[SWAP[0]], MT[SWAP[1]] = MT[SWAP[1]], MT[SWAP[0]]

				# picking an optimal one
				best_SWAP = min(cost, key=cost.get)
				if len(cost) > 1:
					while True:
						if best_SWAP != previous_best_SWAP: break
						else:
							del cost[best_SWAP]
							np.random.seed(datetime.now().microsecond%10)
							best_SWAP = min(cost, key=cost.get)

				# tag if the qubit of the optimal swap is one that should be moved back to home
				if best_SWAP[0] in list_qubits_moved_back:
					list_for_moveback.append(table_moveback[best_SWAP[0]])
				if best_SWAP[1] in list_qubits_moved_back:
					list_for_moveback.append(table_moveback[best_SWAP[1]])

				# update the variables based on the chosen optimal swap
				# decay if the cost function is lap
				listDecay[best_SWAP[0]] += (1+decay)
				listDecay[best_SWAP[1]] += (1+decay)

				# swapping qubit mapping table
				MT[best_SWAP[0]], MT[best_SWAP[1]] = MT[best_SWAP[1]], MT[best_SWAP[0]]
				inverse_MT = {v: k for k, v in MT.items()}

				# to check the type of quantum state 
				name_qubit1, name_qubit2 = best_SWAP[0:2]
					
				while name_qubit1[-1].isdigit(): name_qubit1 = name_qubit1[:-1]
				while name_qubit2[-1].isdigit(): name_qubit2 = name_qubit2[:-1]
				interactions[(name_qubit1, name_qubit2)]+=1
				
				# 두 큐빗이 데이터 류이고, active 상태에 있는 큐빗들간의 SWAP 이면 increment count_data_interaction by 1
				conditionA = "dummy" not in name_qubit1 and table_qubit_status[best_SWAP[0]] == flag_active
				conditionB = "dummy" not in name_qubit2 and table_qubit_status[best_SWAP[1]] == flag_active
				if conditionA and conditionB: count_data_interaction+=1 
				
				# if the amount of the swaps acting on both the data qubits is bigger than the bound,
				# alert!
				if count_data_interaction > number_allowable_data_interaction:
					raise Exception("The number of mutual data interactions reaches to the limit : {} and {}".format(
						count_data_interaction, number_allowable_data_interaction))

				previous_best_SWAP = best_SWAP

				# writing the circuit
				if flag_write_syscode:
					# update qubit mapping by performing the best SWAP
					# to run the system code, it is written with the qubit index not the algorithm qubit name
					# therefore, the algorithm qubit is mapped to the qubit index through the qubit mapping table, MT
					if flag_swap:
						list_syscode_commands.append([g.str_gate_swap, MT[best_SWAP[0]], MT[best_SWAP[1]]])
					# else:
					# 	# swap a, b -> CNOT a, b / CNOT b, a / CNOT a, b
					# 	list_syscode_commands.append([g.str_gate_cnot, MT[best_SWAP[0]], MT[best_SWAP[1]]])
					# 	list_syscode_commands.append([g.str_gate_cnot, MT[best_SWAP[1]], MT[best_SWAP[0]]])
					# 	list_syscode_commands.append([g.str_gate_cnot, MT[best_SWAP[0]], MT[best_SWAP[1]]])

		# after all the gates in FL are performed,
		# if list_for_moveback is not empty, move the elements in the list to FL
		if not len(FL): 
			for k, v in list_for_barrier.items():
				if len(v):
					FL.extend(v)
					list_for_barrier[k] = []

			if not len(FL) and len(list_for_moveback): 
				FL.extend(list_for_moveback)
				list_for_moveback = []

	# check all the data qubits moved their homebase
	if flag_moveback:
		position_data_qubits_after = {key: value for key, value in MT.items() if "data" in key}
		
		if not set(position_data_qubits_after.items()).issubset(set(position_data_qubits.items())):
			raise Exception("The positions of data qubits before and after the mapping is not the same.")
	
	if flag_write_syscode:
		return list_syscode_commands, interactions


def manage_SABRE_as_process(args, conn):
	"""
		function to delegate the execution of graph traversal
		this is because we need to count the time flow and stop if the execution time exceeds the time limit
	"""
	flag_write_syscode = args.get("write_syscode")
	qubit_mapping = args.get("qubit_mapping")
	
	homebase = args.get("homebase")
	
	if homebase is None: position_data_qubits = args.get("position_data_qubits")
	else: position_data_qubits = homebase

	if flag_write_syscode:
		# for the last forward traversal
		list_syscode_commands, interactions = SABRE(args.get("DAG"), args.get("FL"), qubit_mapping, args.get("DM"), args.get("QChip"), 
													qubit_info=args.get("qubit_info"), cost=args.get("cost"), 
													write_syscode=flag_write_syscode, allow_swap=args.get("allow_swap"), 
													position_data_qubits=position_data_qubits,
													direction=args.get("direction"), 
													allowable_data_interaction=args.get("allowable_data_interaction"))

		conn.send([list_syscode_commands, interactions, qubit_mapping])
	
	else:
		# for the first forward and second backward traversals
		SABRE(args.get("DAG"), args.get("FL"), qubit_mapping, args.get("DM"), args.get("QChip"), 
			qubit_info=args["qubit_info"], 
			cost=args["cost"], 
			write_syscode=flag_write_syscode, 
			allow_swap=args["allow_swap"], 
			position_data_qubits=position_data_qubits,
			direction=args.get("direction"), 
			allowable_data_interaction=args["allowable_data_interaction"])

		conn.send([qubit_mapping])



def manage_forward_traversal(args, conn):
	'''
		first forward traversal (with random initial mapping) 관리 함수	
	'''
	qchip_size = len(args["QChip"]["qubit_connectivity"])

	list_algorithm_qubits = []
	for v in args["qubit_info"].values(): list_algorithm_qubits.extend(v)
	
	if args.get("initial_mapping") is not None: 
		flag_write_syscode = True
	else: flag_write_syscode = False

	# fixed_qubit
	qubit_mapping = qubitmapping.initialize_qubit_mapping(list_algorithm_qubits, qchip_size, 
						option=args["initial_mapping_option"], fixed_qubits=args["initial_mapping"], 
						period=args.get("period"))
	
	# 데이터 큐빗의 위치
	# homebase : 프로토콜 수행 후 데이터 큐빗이 위치해야 하는 곳
	# homebase 정보가 없으면, 초기 random mapping 으로 인해 결정된 데이터 큐빗 위치
	homebase = args.get("homebase")

	if homebase is None:
		position_data_qubits = {key: value for key, value in qubit_mapping.items() if "data" in key}
	else:
		position_data_qubits = homebase

	if flag_write_syscode:
		initial_mapping = copy.deepcopy(qubit_mapping)
		list_syscode_commands, interactions = SABRE(args["DAG"], args["FL"], qubit_mapping, args["DM"], args["QChip"], 
													qubit_info=args["qubit_info"], cost=args["cost"], 
													write_syscode=flag_write_syscode, allow_swap=args["allow_swap"], 
													position_data_qubits=position_data_qubits,
													direction="forward", 
													allowable_data_interaction=args["allowable_data_interaction"])
		conn.send([list_syscode_commands, interactions, initial_mapping, qubit_mapping])
	
	else:
		SABRE(args["DAG"], args["FL"], qubit_mapping, args["DM"], args["QChip"], 
													qubit_info=args["qubit_info"], cost=args["cost"], 
													write_syscode=flag_write_syscode, allow_swap=args["allow_swap"], 
													position_data_qubits=position_data_qubits,
													direction="forward", 
													allowable_data_interaction=args["allowable_data_interaction"])

		conn.send([qubit_mapping])


def synthesize(path_QASM, path_qchip, **kwargs):
	
	# options for the circuit synthesis
	synthesis_option = kwargs.get("synthesis_option")		
	if synthesis_option is None:
		raise Exception("Error ! Synthesis option is not provided.")
	
	# cost function for evaluating SWAP candidates (default : lap with depth 1, below) 	
	# cost = {lap, nnc} 	
	cost_function = synthesis_option.get("cost")
	if cost_function is None: cost_function = "lap"
	
	# lap depth (default : 1)
	global lap_depth
	lap_depth = synthesis_option.get("lap_depth")
	if lap_depth is not None: lap_depth = int(lap_depth)
	else: lap_depth = 1
	
	# decay factor (default : 0.1)
	global decay
	decay = synthesis_option.get("decay_factor")
	if decay is not None: decay = float(decay)
	else: decay = 0.1

	# weight for an extended set for looking ahead (default : 0.5)
	global extended_set_weight
	extended_set_weight = synthesis_option.get("extended_set_weight")
	if extended_set_weight is not None: extended_set_weight = float(extended_set_weight)
	else: extended_set_weight = 0.5
	
	# criterion for optimality of the circuit ()
	# optimal_criterion = {circuit_depth, number_gates} 	
	optimal_criterion = synthesis_option.get("optimal_criterion")
	if optimal_criterion is None:
		optimal_criterion = "circuit_depth"
	
	# option for picking an initial mapping {random, periodic_random, fixed, ..}
	# please see the package qubitmapping
	initial_mapping_option = synthesis_option.get("initial_mapping_option")
	if initial_mapping_option is None:
		initial_mapping_option = "random"

	# SABRE iteration (default : 10)
	iteration = synthesis_option.get("iteration")
	if iteration is not None: iteration = int(iteration)
	else: iteration = 10

	# write a best circuit to a file
	base_qasm = os.path.splitext(os.path.basename(path_QASM))[0]
	base_qchip = os.path.splitext(os.path.basename(path_qchip))[0]
	
	flag_initial_mapping = False
	# check a qubit mapping is provided
	initial_mapping = kwargs.get("qubit_table")
	if initial_mapping is not None:
		if len(initial_mapping): flag_initial_mapping = True

	json_qchip_data = open(path_qchip).read()
	qchip_data = json.loads(json_qchip_data)

	# update qubit connectivity (string type -> int type)	
	qchip_data["qubit_connectivity"] = {int(k): v for k, v in qchip_data["qubit_connectivity"].items()}
	qchip_size = len(qchip_data["qubit_connectivity"].keys())

	# the dimension of quantum chip 
	# in case of 2d lattice : height x width
	# otherwise : 1 x width
	qchip_lattice_size = qchip_data.get("dimension")
	if qchip_lattice_size is None:
		qchip_lattice_size = {"height": 1, "width": qchip_size}
	
	# computing the distance matrix from qchip_data
	retDM, _ = DM.generateDM(qchip_data, "distance")
	
	# option for supporting a swap gate (default : true)
	# otherwise, a swap is implemented as 3 cnot gates
	flag_swap = synthesis_option.get("allow_swap")
	if flag_swap is None: flag_swap = True
		
	# the bound for allowing the interaction (swap) between data qubits
	allowable_data_interaction = synthesis_option.get("allowable_data_interaction")
	if allowable_data_interaction is None: allowable_data_interaction = 0
	else: allowable_data_interaction = int(allowable_data_interaction)

	# reference variables to hold the optimal performance and circuits
	# initialized as math.inf or 0 	
	min_circuit_depth = math.inf
	min_data_move = math.inf
	optimal_performance = math.inf
	best_initial_mapping = None
	best_circuit = None
	best_interaction = None
	best_syscode = []

	# types of qubits used in the protocol
	qubit_info = collections.defaultdict(list)

	# pre-analyze a qasm code
	list_qasm_commands, list_algorithm_qubits, cnot_counts = SABRE_utility.analyze_qasm(path_QASM)

	# classify algorithm_qubits into groups according to the qubit array name
	# such as "data", "ancilla", "syndrome"
	for qubit in list_algorithm_qubits:
		tokens_qubit_name = qubit.split("-")
		if len(tokens_qubit_name) == 1: qubit_name = tokens_qubit_name[0]
		elif len(tokens_qubit_name) == 2: qubit_name = tokens_qubit_name[1]
		
		result = parse.compile("{}[{}]").parse(qubit_name)
		
		if result is not None: 
			qubit_name = result[0]
			qubit_info[qubit_name].append(qubit)
		
		else:
			while qubit_name[-1].isdigit(): qubit_name = qubit_name[:-1]
			qubit_info[qubit_name].append(qubit)

		# the name of a qubit differs according to a FT protocol
		# in case of cnot and t, it has "LQ1" or "LQ2" at the beginning (e.g., "LQ1-data", "LQ2-magic")
		# to distinguish the logical qubit and physical qubit, we split the qubit name by "-"

	# renaming the data qubits for the moveback
	# case 1: syndrome measurement & clifford gates: data[i] --> data[i]_init
	# case 2: Magic State Preparation: 
	# case 3: T Gate: measure magic state --> data qubit to its home
	
	# flag for moveback, it depends on a protocol
	# flag to include the moveback or not
	flag_moveback = synthesis_option.get("moveback")

	# homebase : position for the data qubits should be placed at the end of the circuit
	# 			 obviously, the destination of the moveback is homebase
	# 			 otherwise, the data qubit will be back to its initial position
	homebase = synthesis_option.get("homebase")

	# when the homebase information is provided,
	# the destination of the moveback is set with the homebase
	# otherwise, the initial position from the picked initial mapping is set for that
	# for the data qubits only, the moveback is conducted
	list_qubits_moved_back = []
	if flag_moveback:
		# if homebase is not specified, then it is automatically set with the initial positions from the initial mapping
		if homebase is None:
			for qubit in qubit_info["data"]:
				list_qubits_moved_back.append(qubit)
				list_qasm_commands.append([g.str_move, qubit, "{}-init".format(qubit)])
		else:
			for qubit in qubit_info["data"]:
				list_qubits_moved_back.append(qubit)
				list_qasm_commands.append([g.str_move, qubit, homebase[qubit]])	

	# directed acyclic graph for forward traversal
	retDAG = DirectedAcyclicGraph.createDAG(list_qasm_commands)
	
	# for the backward traversal, 
	# the inserted moveback instruction should be removed
	if flag_moveback:
		if homebase is None:
			for qubit in list_qubits_moved_back:
				list_qasm_commands.remove([g.str_move, qubit, "{}-init".format(qubit)])
		else:
			for qubit in list_qubits_moved_back:
				list_qasm_commands.remove([g.str_move, qubit, homebase[qubit]])	

	print("list of the qubits for move-back : ", list_qubits_moved_back)

	# directed acyclic graph for backware traversal
	reverseDAG = DirectedAcyclicGraph.createDAG(reversed(list_qasm_commands))

	# arguments for graph traversal
	arguments = {"QChip": qchip_data, 
				 "DM": retDM, 
				 "qubit_info": qubit_info, 
				 "initial_mapping": initial_mapping,
				 "initial_mapping_option": initial_mapping_option,
				 "period": synthesis_option.get("period"),
 			 	 "DAG": retDAG["DAG"], 
 			 	 "cost": cost_function, 
 			 	 "allow_swap": flag_swap,
 			 	 "allowable_data_interaction": allowable_data_interaction,
 			 	 "homebase": homebase}
	
	if cnot_counts: time_limit = cnot_counts
	else: time_limit = 10

	flag_must = False

	bar = Bar ('Progress', max=iteration)

	while True:
		iter_idx = 0
		while iter_idx < iteration:
			# clone the front layer
			FL = copy.deepcopy(retDAG["roots"])
			arguments.update({"FL": FL})

			# if the traveral is not succeeded, the following traversals will not succeed
			# perform the first forward graph traversal indepently (as a separate process)
			parent_conn, child_conn = multiprocessing.Pipe(duplex=False)
			ps = multiprocessing.Process(target=manage_forward_traversal, args=(arguments, child_conn))
			ps.start()

			if not flag_must: ps.join(time_limit)
			else: ps.join()

			# if the process is alive after the pre-set timelimt,
			# it will be killed
			if ps.is_alive():
				ps.terminate()
				print(" time limit !")
				continue

			else:
				# result of the first forward graph traversal
				message = parent_conn.recv()

				if flag_initial_mapping:
					list_syscode_commands, interactions, initial_mapping, final_mapping = message[:]
				
				# initial qubit mapping 이 주어지지 않았으면, forward-reverse-forward traversal 을 통해서 최적의 mapping 을 찾아야 함
				# initial qubit mapping (partial)이 주어졌으면, 해당 mapping 이 유지되어야 하므로 forward traversal 만 수행함
				else:
					# arguments for the backward traversal
					qubit_mapping = message[0]
					in_arguments = {"QChip": qchip_data, 
									"DM": retDM, 
									"qubit_mapping": qubit_mapping,
									"DAG": reverseDAG["DAG"], "FL": reverseDAG["roots"],
									"cost": cost_function, "write_syscode": False, "allow_swap": flag_swap,
									"direction": "backward", "qubit_info": qubit_info,
									"allowable_data_interaction": allowable_data_interaction,
									"homebase": homebase}

					# for backward graph traversal as a separate process
					parent_conn, child_conn	= multiprocessing.Pipe(duplex=False)
					ps = multiprocessing.Process(target=manage_SABRE_as_process, args=(in_arguments, child_conn))
					ps.start()

					if not flag_must: ps.join(time_limit)
					else: ps.join()

					if ps.is_alive():
						ps.terminate()
						print(" time limit !")
						continue
					
					message = parent_conn.recv()
					qubit_mapping = message[0]

					# for the last forward traversal, collect qubit mapping data from the previous backward traversal
					initial_mapping = copy.deepcopy(qubit_mapping)
					position_data_qubits = {key: value for key, value in qubit_mapping.items() if "data" in key}

					# final forward traverse circuit
					FL = copy.deepcopy(retDAG["roots"])
					# arguments for the final forward graph traversal
					in_arguments = {"QChip": qchip_data, "DM": retDM, "qubit_mapping": qubit_mapping,
								 	"DAG": retDAG["DAG"], "FL": FL, "cost": cost_function, "write_syscode": True, "allow_swap": flag_swap,
								 	"qubit_info": qubit_info, "position_data_qubits": position_data_qubits, "direction": "forward",
								 	"allowable_data_interaction": allowable_data_interaction,
								 	"homebase": homebase}

					ps = multiprocessing.Process(target=manage_SABRE_as_process, args=(in_arguments, child_conn))
					ps.start()

					if not flag_must: ps.join(time_limit)
					else: ps.join()

					if ps.is_alive():
						ps.terminate()
						print(" time limit !")
						continue
					
					# circuit data from the last forward graph traversal
					message = parent_conn.recv()
					list_syscode_commands, interactions, qubit_mapping = message[:]						
					final_mapping = copy.deepcopy(qubit_mapping)
				
				iter_idx+=1
				
				# cancel out the redundant data if exist
				list_syscode_commands = formatconversion.cancel_redundancy(list_syscode_commands)

				# evaluate the circuit in terms of the circuit depth or number of gates
				# and pick the best one 
				if optimal_criterion == "circuit_depth":
					circuit_depth = depth_analysis.evaluate_circuit_depth(list_syscode_commands)
						
					if circuit_depth < optimal_performance:
						optimal_performance = circuit_depth
						best_syscode = list_syscode_commands
						min_data_move = sum(v for k, v in interactions.items() if any("data" in qubit for qubit in [k[0], k[1]]))
					
						best_initial_mapping = copy.deepcopy(initial_mapping)
						best_final_mapping = copy.deepcopy(final_mapping)
						best_interaction = interactions

				elif optimal_criterion == "number_gates":
					# gate 수 기준으로 optimal circuit 찾기
					number_instructions = len(list_syscode_commands)

					if number_instructions < optimal_performance:
						optimal_performance = number_instructions
						best_syscode = list_syscode_commands
						min_data_move = sum(v for k, v in interactions.items() if any("data" in qubit for qubit in [k[0], k[1]]))
					
						best_initial_mapping = copy.deepcopy(initial_mapping)
						best_final_mapping = copy.deepcopy(final_mapping)
						best_interaction = interactions

			bar.next()
		
		# if the best mapping is provided, then break the loop
		# otherwise, we need to iterate the loop 1 time again
		if not best_initial_mapping is None: break
		else:
			flag_must = True
			iteration = 1

	bar.finish()

	# form a time ordered system code from the naive list
	best_circuit = formatconversion.transform_ordered_syscode(best_syscode, qchip_size)	
	
	# checkup the mapping result is compatible with the given qubit connectivity
	if checkup.checkup_system_code(best_circuit, best_initial_mapping, qchip_data):
		checkup_msg = "mapping result is compatible with the given qubit connectivity."
	else:
		checkup_msg = "mapping result is NOT compatible with the given qubit connectivity."
		raise Exception("mapping result is NOT compatible with the given qubit connectivity.")
	
	# analyze the list of quantum gates used in the protocol
	function_list = collections.defaultdict(int)
	for inst in best_syscode: function_list[inst[0]]+=1

	# analyze the quantity of cnot gates (with swap)
	cnot_analysis = {"Algorithm": cnot_counts,
					 "Circuit": function_list["CNOT"] + 3*function_list["SWAP"]}
	cnot_analysis.update({"Overhead": cnot_analysis["Circuit"] - cnot_analysis["Algorithm"]})				 

	# in the "system_code" mode, the generated system code is written into a file 
	time_ordered_circuit = {"circuit": best_circuit,
							"initial_mapping": best_initial_mapping,
							"final_mapping": best_final_mapping}

	# information about the interaction among the qubits
	if best_interaction is not None and len(best_interaction):
		best_interaction = {"-".join([k[0],k[1]]): v for k, v in best_interaction.items()}

	
	# circuit depth
	circuit_depth = max(list(best_circuit.keys()))+1
	
	# kq of the circuit = the circuit depth x the circuit bandwidth (# qubits)
	kq = circuit_depth * len(best_final_mapping.keys())
	
	# the data for returning
	ret = {"system_code": time_ordered_circuit,
		   "qchip": qchip_data,
		   "analysis": {"Qubit": {"Qubit": len(best_final_mapping.keys()), 
		   						  "Layout Size": qchip_data["dimension"]},
		   				"Function List": function_list,
		   				"CNOT Overhead": cnot_analysis,
		   				"Data Qubit Move": min_data_move,
		   				"Circuit Depth": circuit_depth,
		   				"Interaction": best_interaction,
		   				"KQ": kq},
		   	"checkup": checkup_msg}
	
	return ret


if __name__ == "__main__":
	path_qasm = os.path.join("../", "Stabilizer_Measure_steaneEC.qasmf")
	path_qchip = os.path.join("../", "file_qchip_7x7.json")

	synthesis_option={"lap_depth": 5, "iteration": 10, "cost": "lap", "moveback": True,
						"optimal_criterion" : "circuit_depth", "initial_mapping_option": "periodic_random"}
	
	ret = synthesize(path_qasm, path_qchip, synthesis_option=synthesis_option)
	
	checkup.checkup_fault_tolerance(ret["system_code"], ret["qchip"]["dimension"])
