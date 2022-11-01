# -*-coding:utf-8-*-

# This code is part of ftsynthesis
# (fault-tolerant quantum circuit synthesis for fault-tolerant quantum protocols)
#
# Copyright 2022 ETRI
#
# This code is licensed under the BSD-3-Clause.

'''
    module to form the resulting circuit
'''

import collections
from math import *
from ast import literal_eval
from pprint import pprint

import globalVariable as g


def get_bigger(operand1, operand2):
    """
        function to find bigger data
    """
    if operand1 > operand2:
        return operand1
    return operand2


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
                last_inst_a = table[inst[1]][-1]
                last_inst_b = table[inst[2]][-1]

                condition_a = (last_inst_a["gate"] == inst[0]) and \
                              (last_inst_a["qubits"] == inst[1:])

                condition_b = (last_inst_b["gate"] == inst[0]) and \
                              (last_inst_b["qubits"] == inst[1:])

                # 동일하면
                if condition_a and condition_b:
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
                last_inst_a = table[inst[1]][-1]
                last_inst_b = table[inst[2]][-1]

                condition_a = (last_inst_a["gate"] == inst[0]) and \
                             (set(last_inst_a["qubits"]) == set(inst[1:]))
                condition_b = (last_inst_b["gate"] == inst[0]) and \
                             (set(last_inst_b["qubits"]) == set(inst[1:]))

                # 동일하면
                if condition_a and condition_b:
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
                    new_angle = float(literal_eval(last_inst["angle"])) +\
                                float(literal_eval(inst[1]))
                    table[inst[2]][-1]["angle"] = str(new_angle)

                else:
                    table[inst[2]].append({"gate": inst[0], "qubits": [inst[2]],
                                           "idx": idx, "angle": inst[1]})
            else:
                table[inst[2]].append({"gate": inst[0], "qubits": [inst[2]],
                                       "idx": idx, "angle": inst[1]})

        elif inst[0] in [g.str_gate_u]:
            if len(table[inst[2]]):
                last_inst = table[inst[2]][-1]
                if last_inst["gate"] == inst[0] and last_inst["qubits"] == inst[2:]:
                    new_angle = {}
                    for axis in ["x", "z", "y"]:
                        new_angle[axis] = float(literal_eval(last_inst["angle"][axis])) +\
                                          float(literal_eval(inst[1][axis]))
                    table[inst[2]][-1]["angle"] = new_angle
                else:
                    table[inst[2]].append({"gate": inst[0], "qubits": [inst[2]],
                                           "angle": inst[1], "idx": idx})
            else:
                table[inst[2]].append({"gate": inst[0], "qubits": [inst[2]],
                                       "angle": inst[1], "idx": idx})

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
        for val in v_list:
            temp_syscode[val["idx"]] = val

    sorted_index = sorted(temp_syscode.keys())

    post_processed_syscode = []
    for k in sorted_index:
        val = temp_syscode[k]
        if val["gate"] in [g.str_gate_cnot, g.str_gate_cz, g.str_gate_swap]:
            post_processed_syscode.append([val["gate"], val["qubits"][0], val["qubits"][1]])

        elif val["gate"] in [g.str_gate_measz, g.str_gate_measx]:
            post_processed_syscode.append([val["gate"], val["qubits"][0], val["qubits"][0]])

        elif val["gate"] in [g.str_gate_rz, g.str_gate_u]:
            post_processed_syscode.append([val["gate"], val["angle"], val["qubits"][0]])

        # barrier-all
        elif val["gate"] == g.str_barrier_all:
            post_processed_syscode.append([val["gate"]])

        # selective barrier
        elif val["gate"] == g.str_barrier:
            post_processed_syscode.append([val["gate"], val["qubits"]])

        else:
            post_processed_syscode.append([val["gate"], val["qubits"][0]])

    return post_processed_syscode


def transform_time_ordered_syscode(syscode, qubit_mapping):
    """
        function to transform a system code of the list form without time information into
        time ordered form in a dictionary
    """

    inverse_qubit_mapping = {v: k for k, v in qubit_mapping.items()}

    collections_qubits = collections.defaultdict(lambda: collections.defaultdict(bool))

#     list_working_qubits = []
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
            while qubit_type[-1].isdigit():
                qubit_type = qubit_type[:-1]
            collections_qubits[qubit_type][qubit_name] = True

            circuit[qubit_time_index[qubit_name]].append(inst)
            qubit_time_index[qubit_name]+=1

        elif inst[0] in [g.str_gate_measz, g.str_gate_measx]:
            qubit_index = inst[1]
            qubit_name = inverse_qubit_mapping[qubit_index]

            qubit_type = qubit_name
            while qubit_type[-1].isdigit():
                qubit_type = qubit_type[:-1]
            collections_qubits[qubit_type][qubit_name] = False

            circuit[qubit_time_index[qubit_name]].append(inst)
            qubit_time_index[qubit_name] += 1

            if not any(collections_qubits[qubit_type].values()):
                collections_circuits[circuit_index] = circuit
                for qubit in qubit_time_index.keys():
                    qubit_time_index[qubit] = 0

                circuit = collections.defaultdict(list)
                circuit_index+=1
        else:
            qubit_index = inst[1]
            qubit_name = inverse_qubit_mapping[qubit_index]

            circuit[qubit_time_index[qubit_name]].append(inst)
            qubit_time_index[qubit_name]+=1

    inverse_qubit_mapping = {v: k for k, v in qubit_mapping.items()}

    for circuit in list(collections_circuits.values()):
        for instructions in list(circuit.values()):
            for inst in instructions:
                if inst[0] in [g.str_gate_swap, g.str_gate_cnot]:
                    print(inst, inst[0], inverse_qubit_mapping[inst[1]],
                          inverse_qubit_mapping[inst[2]])

                    if inst[0] == g.str_gate_swap:
                        inverse_qubit_mapping[inst[1]], inverse_qubit_mapping[inst[2]] =\
                            inverse_qubit_mapping[inst[2]], inverse_qubit_mapping[inst[1]]
                else:
                    print(inst, inst[0], inverse_qubit_mapping[inst[1]])
        print("\n")

    pprint(collections_circuits)


def transform_ordered_syscode(syscode, **kwargs):
    '''
        개별 게이트의 circuit index를 분석하고, 시간순으로 정리된 회로를 생성 리턴하는 함
    '''

    time_index = collections.defaultdict(int)
    ordered_syscode = collections.defaultdict(list)

    for inst in syscode:
        flag_barrier = False

        if inst[0] in [g.str_gate_cnot, g.str_gate_cz, g.str_gate_swap]:
            ctrl, trgt = inst[1:]

            applying_index = max(time_index[ctrl], time_index[trgt])
            time_index[ctrl] = time_index[trgt] = applying_index+1
            list_command = f"{inst[0]} {ctrl},{trgt}"

        elif inst[0] in ["Qubit", "Cbit"]:
            continue

        else:
            if inst[0] in [g.str_gate_rz, g.str_gate_rx, g.str_gate_ry, g.str_gate_phase]:
                angle, qubit = inst[1:]
                list_command = f"{inst[0]}({angle}) {qubit}"
                applying_index = time_index[qubit]
                time_index[qubit] += 1

            elif inst[0] in [g.str_gate_u]:
                *angle, qubit = inst[1:]
                list_command = f"{inst[0]}({angle[0]},{angle[1]},{angle[2]}) {qubit}"
                applying_index = time_index[qubit]
                time_index[qubit] += 1

            elif inst[0] in [g.str_gate_measz, g.str_gate_measx]:
                qubit, cbit, *arguments = inst[1:]
                list_str_command = [inst[0], str(qubit), "->", str(cbit)]

                if len(arguments):
                    sub_args_command = []
                    str_args = ",".join(sub_args_command)
                    str_args = "(" + str_args + ")"
                    list_str_command.append(str_args)

                list_command = " ".join(list_str_command)

                applying_index = time_index[qubit]
                time_index[qubit] += 1

            elif inst[0] in ["Qubit"]:
                if len(inst[1:]) == 2:
                    qubit, size = inst[1:]
                    list_command = f"{inst[0]} {qubit} {size}"
                else:
                    qubit = inst[1]
                    list_command = f"{inst[0]} {qubit}"

            elif inst[0] == g.str_barrier_all:
                flag_barrier = True
                list_command = g.str_barrier_all
                applying_index = max(list(time_index.values()))

                for qubit in time_index.keys():
                    time_index[qubit] = applying_index

            elif inst[0] == g.str_barrier:
                flag_barrier = True
                list_command = f"{g.str_barrier} {inst[1]}"
                applying_index = max(time_index[qubit] for qubit in inst[1])

                for qubit in inst[1]:
                    time_index[qubit] = applying_index

            else:
                qubit = inst[1]
                list_command = f"{inst[0]} {qubit}"
                applying_index = time_index[qubit]
                time_index[qubit] += 1

        if flag_barrier:
            applying_index -= 1

        ordered_syscode[applying_index].append(list_command)

    return ordered_syscode
