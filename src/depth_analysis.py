# -*-coding:utf-8-*-

# This code is part of ftsynthesis
# (fault-tolerant quantum circuit synthesis for fault-tolerant quantum protocols)
#
# Copyright 2022 ETRI
#
# This code is licensed under the BSD-3-Clause.

'''
    module to evaluate the depth of the resulting circuit
'''

import collections
import networkx

import DirectedAcyclicGraph
import globalVariable as g


def get_bigger(operand1, operand2):
    """
        function to find bigger data
    """
    if operand1 > operand2:
        return operand1
    return operand2


def evaluate_circuit_depth(list_syscode_commands):
    """
        function to evaluate the circuit depth of a circuit
    """
    qubit_depth = collections.defaultdict(int)

    for inst in list_syscode_commands:
        if inst[0] in [g.str_gate_cnot, g.str_gate_swap, g.str_gate_cz]:
            ctrl, trgt = inst[1:]
            apply_index = get_bigger(qubit_depth[ctrl], qubit_depth[trgt])
            qubit_depth[ctrl] = qubit_depth[trgt] = apply_index+1

        elif inst[0] == g.str_barrier_all:
            for qubit in qubit_depth.keys():
                qubit_depth[qubit]+=1

        elif inst[0] == g.str_barrier:
            for qubit in inst[1]:
                qubit_depth[qubit]+=1

        elif inst[0] in [g.str_gate_rz]:
            # rz gate : Rz angle trgt_qubit
            qubit = inst[2]
            qubit_depth[qubit]+=1

        else:
            qubit = inst[1]
            qubit_depth[qubit]+=1

    # in general, the depth of the circuit is determined from the maximum value of
    # all the qubits's operation time
    return max(list(qubit_depth.values()))


def evaluate_t_depth(system_code):
    """
        function to evaluate the t-depth of a circuit
    """

    t_depth = collections.defaultdict(int)

    for inst in system_code["circuit"]:
        # T, Tdag gates are reflected to count the t-depth
        if inst[0] in ["T", "Tdag"]:
            t_depth[inst[1]] += 1

        elif inst[0] in ["CNOT"]:
            t_depth[inst[1]] = get_bigger(t_depth[inst[1]], t_depth[inst[2]])
            t_depth[inst[2]] = t_depth[inst[1]]

    return max(t_depth.values())


def evaluate_cnot_depth(system_code):
    """
        function to evaluate the cnot-depth of a circuit
        it is determined from the directed acyclic graph with the longest path
    """

    circuit_dag = DirectedAcyclicGraph.createDAG(system_code["circuit"], goal="cnot_depth")
    cnot_depth = networkx.dag_longest_path_length(circuit_dag["DAG"]) + 1

    return cnot_depth
