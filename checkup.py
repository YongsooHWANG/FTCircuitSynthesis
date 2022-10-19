
import re
import pandas
from icecream import ic
import globalVariable as g


def checkup_system_code(system_code, mapping_table, qchip, **kwargs):
	"""
		function to checkup of the circuit whether the system_code is compatible with the quantum chip (qubit connectivity)
	"""
	
	parser = re.compile("[\{a-zA-Z0-9_.*\->\+}]+")
	flag_verification = True
	
	if type(system_code) == dict:
		for instructions in list(system_code.values()):
			for inst in instructions:
				tokens = parser.findall(inst)
				if not len(tokens): continue
				
				if tokens[0] in [g.str_gate_cnot, g.str_gate_swap, g.str_gate_cz]:
					ctrl, trgt = map(int, tokens[1:])
					if trgt not in qchip["qubit_connectivity"][ctrl]:
						flag_verification = False
						break

	elif type(system_code) == list:
		for inst in system_code:
			if inst[0] in [g.str_gate_cnot, g.str_gate_swap, g.str_gate_cz]:
				ctrl, trgt = map(int, inst[1:])
				if trgt not in qchip["qubit_connectivity"][ctrl]:
					flag_verification = False
					break

	return flag_verification


def checkup_fault_tolerance(system_code, lattice_size, **kwargs):
    '''
        function to investigate the fault tolerance of the circuit
    '''

    # initial mapping
    qubit_mapping = system_code["initial_mapping"]
    inverse_mapping = {v: k for k, v in qubit_mapping.items()}

    layout = [[0 for i in range(lattice_size["width"])] for j in range(lattice_size["height"])]
    
    for idx, qubit in inverse_mapping.items():
        x_coord = int(idx/lattice_size["width"])
        z_coord = int(idx%lattice_size["width"])

        layout[x_coord][z_coord] = qubit
    
    print(" =====================================================  ")
    print("Initial Mapping: ")
    print(" -----------------------------------------------------  ")
    print(pandas.DataFrame(layout).to_string())
    print(" =====================================================  ")

    circuit_depth = max(list(system_code["circuit"].keys())) + 1
    
    qubit_usage_status = {k: True if "data" in k else False for k in qubit_mapping.keys()}

    ic(qubit_usage_status)

    # circuit
    for idx in range(circuit_depth):
        instructions = system_code["circuit"][idx]

        flag_swap = False
        print(" =====================================================  ")
        print("instructions at {}-th index : {}".format(idx, instructions))
        print(" -----------------------------------------------------  ")
        
        for inst in instructions:
            tokens = inst.split(" ")

            if tokens[0] in ["PrepZ"]:
                physical_qubit = int(tokens[1])
                logical_qubit = inverse_mapping[physical_qubit]
                
                print(" {} {} ({}) -> {}".format(tokens[0], physical_qubit, logical_qubit, qubit_usage_status[logical_qubit]))

                qubit_usage_status[logical_qubit] = True

            elif tokens[0] in ["MeasZ"]:
                physical_qubit = int(tokens[1])
                logical_qubit = inverse_mapping[physical_qubit]

                print(" {} {} ({}) -> {}".format(tokens[0], physical_qubit, logical_qubit, qubit_usage_status[logical_qubit]))

                qubit_usage_status[logical_qubit] = False

            elif tokens[0] in ["CNOT"]:
                qubits = list(map(int, tokens[1].split(",")))
                
                print(" {} {}, {} ({}, {}) -> {}, {}".format(tokens[0], qubits[0], qubits[1], inverse_mapping[qubits[0]], inverse_mapping[qubits[1]],
                											qubit_usage_status[inverse_mapping[qubits[0]]], qubit_usage_status[inverse_mapping[qubits[1]]]))

                flag_swap = False

            elif tokens[0] in ["SWAP"]:
                qubits = list(map(int, tokens[1].split(",")))
                print(" {} qubits ({}, {}) -> ({}, {}) {} {}".format(tokens[0], qubits[0], qubits[1], inverse_mapping[qubits[0]], inverse_mapping[qubits[1]],
                                                                    qubit_usage_status[inverse_mapping[qubits[0]]], qubit_usage_status[inverse_mapping[qubits[1]]]))

                inverse_mapping[qubits[0]], inverse_mapping[qubits[1]] =\
                    inverse_mapping[qubits[1]], inverse_mapping[qubits[0]]
                
                flag_swap = True

                # activated 큐빗간 interaction (SWAP)에 대해서, 오류 발생시킴
                if qubit_usage_status[logical_qubit0] and qubit_usage_status[logical_qubit1]:
                    raise error.Error("Stop: SWAP between activated qubits")

            # barrier - All : for all qubits
            elif tokens[0] in [g.str_barrier_all]:
                print(" {} ".format(tokens[0]))
                flag_swap = False

            # selective barrier for selected qubits
            elif tokens[0] in [g.str_barrier]:
                print(" {} {}".format(tokens[0], tokens[1:]))
                ic(inverse_mapping)
                flag_swap = False
            
            else:
                qubit = int(tokens[1])
                print(" {} {} ({})".format(tokens[0], qubit, inverse_mapping[qubit]))
                flag_swap = False

        if flag_swap:
            # form 2d array
            for idx, qubit in inverse_mapping.items():
                x_coord = int(idx/lattice_size["width"])
                z_coord = int(idx%lattice_size["width"])

                layout[x_coord][z_coord] = qubit

        print(" -----------------------------------------------------  ")
        print(pandas.DataFrame(layout).to_string())
        print(" =====================================================  ")	