# -*-coding:utf-8-*-

# This code is part of ftsynthesis
# (fault-tolerant quantum circuit synthesis for fault-tolerant quantum protocols)
#
# Copyright 2022 ETRI
#
# This code is licensed under the BSD-3-Clause.

'''
    module to generate_directed_acyclic_graph
'''

import collections
import itertools
from ast import literal_eval
import parse

import networkx as nx

import globalVariable as g

def createDAG(list_qasm, **kwargs):
    '''
         function to generate directed_acyclic graph from the given QASM
    '''
    DAG = nx.DiGraph()

    # 노드 증가할 때 마다 1씩 increment
    node_index = 0
    list_nodes_associated_with_qubit = collections.defaultdict(list)
    list_nodes_connection = []
    list_root_nodes = []
    list_qubits = []

    for tokens in list_qasm:
        if tokens[0] in [g.str_gate_cnot, g.str_gate_cz, g.str_move_back, g.str_move,
                         g.str_gate_cx, g.str_gate_swap]:
            ctrl, trgt = tokens[1:3]

            # DAG 노드 생성
            DAG.add_node(node_index, gate=tokens[0], ctrl=ctrl, trgt=trgt, id=node_index)

            # current 노드가 DAG의 root 인지 확인하기 위한 flag
            flag_children = False

            # current 노드로 연결되는 부모 노드가 있는지 확인하는 단계
            # 공유하는 큐빗의 유무로 부모-자식 관계 결정됨
            if len(list_nodes_associated_with_qubit[ctrl]):
                flag_children = True
                parent_node_id = list_nodes_associated_with_qubit[ctrl][-1]
                list_nodes_connection.append((parent_node_id, node_index))

            # ctrl/trgt 큐빗을 공유하는 그래프 상의 마지막 노드에 현재 노드 추가
            list_nodes_associated_with_qubit[ctrl].append(node_index)

            # move 의 경우, trgt 가 "measurement_qubit" 이면, trgt 에 대해서는 무시함
            if tokens[0] not in [g.str_move] and trgt != "measurement_qubit":
                if len(list_nodes_associated_with_qubit[trgt]):
                    flag_children = True
                    parent_node_id = list_nodes_associated_with_qubit[trgt][-1]
                    list_nodes_connection.append((parent_node_id, node_index))

                list_nodes_associated_with_qubit[trgt].append(node_index)

            # 부모 노드 없으면, 현재 노드가 root 노드에 해당함
            if not flag_children:
                list_root_nodes.append(DAG.nodes[node_index])

        elif tokens[0] in g.list_one_qubit_gates:
            # measurement
            if tokens[0] in [g.str_gate_measz, g.str_gate_measx]:
                arguments = []

                cbit = None
                if len(tokens) == 2:
                    trgt = tokens[1]
                elif len(tokens) == 3:
                    trgt, cbit = tokens[1:]
                else:
                    trgt, cbit, *arguments = tokens[1::2]

                if len(arguments) == 0:
                    DAG.add_node(node_index, gate=tokens[0], trgt=trgt, cbit=cbit,
                                 id=node_index)

                else:
                    for value in arguments:
                        if isinstance(value, int):
                            DAG.add_node(node_index, gate=tokens[0], trgt=trgt, cbit=cbit,
                                         id=node_index, expected=value)
                        else:
                            DAG.add_node(node_index, gate=tokens[0], trgt=trgt, cbit=cbit,
                                         id=node_index, role=value)

            # rotational gate
            elif tokens[0] in [g.str_gate_rz, g.str_gate_rx, g.str_gate_ry, g.str_gate_phase]:
                angle, trgt = tokens[1:]
                # QASM 구조가 Gate qubit angle 순 (이전 버전) 이면, Gate angle qubit 순으로 바꿔 해석함
                # 즉, qubit 과 angle 을 서로 교환함
                try:
                    if isinstance(literal_eval(trgt), float):
                        angle, trgt = trgt, angle
                # except Exception:
                #     pass

                finally:
                    DAG.add_node(node_index, gate=tokens[0], trgt=trgt, angle=angle,
                                 id=node_index)

            elif tokens[0] in [g.str_gate_u]:
                # u 게이트 (IBM QX 경우) 이면, 세 각도가 모두 입력됨
                angle_x, angle_y, angle_z, trgt = tokens[1:]
                DAG.add_node(node_index, gate=tokens[0], trgt=trgt,
                             angle={"x":angle_x, "y":angle_y, "z": angle_z}, id=node_index)

            # else Hadamard, Pauli..
            else:
                trgt = tokens[1]
                DAG.add_node(node_index, gate=tokens[0], trgt=trgt, id=node_index)

            flag_children = False

            if len(list_nodes_associated_with_qubit[trgt]):
                flag_children = True
                parent_node_id = list_nodes_associated_with_qubit[trgt][-1]
                list_nodes_connection.append((parent_node_id, node_index))

            if not flag_children:
                list_root_nodes.append(DAG.nodes[node_index])

            list_nodes_associated_with_qubit[trgt].append(node_index)
            # list_nodes_associated_with_qubit[ctrl].append(node_index)


        elif tokens[0] in ["Release"]:
            # qubit array 이름은 tokens[1]
            # 해당 qubit array 의 모든 인덱스에 대해서, Release 하는 명령을 추가함
            # 따라서,
            # array 이름
            target_qubit_array_name = tokens[1]
            # 현재까지 사용된 큐빗들 목록 : list_nodes_associated_with_qubit.keys()

            if len(list_nodes_associated_with_qubit.keys()):
                for qubit in list_nodes_associated_with_qubit.keys():
                    if target_qubit_array_name in qubit:
                        DAG.add_node(node_index, gate="Release", trgt=qubit, id=node_index)

                        flag_children = False
                        if len(list_nodes_associated_with_qubit[qubit]):
                            flag_children = True
                            parent_node_id = list_nodes_associated_with_qubit[qubit][-1]
                            list_nodes_connection.append((parent_node_id, node_index))

                        if not flag_children:
                            list_root_nodes.append(DAG.nodes[node_index])

                        list_nodes_associated_with_qubit[qubit].append(node_index)

                        node_index+=1
            else:
                DAG.add_node(node_index, gate="Release", trgt=target_qubit_array_name,
                            id=node_index)
                list_root_nodes.append(DAG.nodes[node_index])
                node_index+=1

        elif tokens[0] == g.str_barrier:
            list_qubits = tokens[1:]
            DAG.add_node(node_index, gate=g.str_barrier, trgt=list_qubits, id=node_index)

            for qubit in list_qubits:
                if len(list_nodes_associated_with_qubit[qubit]):
                    parent_node_id = list_nodes_associated_with_qubit[qubit][-1]
                    list_nodes_connection.append((parent_node_id, node_index))
                else:
                    list_root_nodes.append(DAG.nodes[node_index])

                list_nodes_associated_with_qubit[qubit].append(node_index)

        elif tokens[0] in [g.str_barrier_all]:
            DAG.add_node(node_index, gate=tokens[0], id=node_index)

            for qubit in list_nodes_associated_with_qubit.keys():
                if len(list_nodes_associated_with_qubit[qubit]):
                    parent_node_id = list_nodes_associated_with_qubit[qubit][-1]
                    list_nodes_connection.append((parent_node_id, node_index))
                else:
                    list_root_nodes.append(DAG.nodes[node_index])

                list_nodes_associated_with_qubit[qubit].append(node_index)

        elif tokens[0] in ["Qubit"]:
            trgt = tokens[1]
            result = parse.compile("{}[{}]").parse(trgt)

            if result is None:
                DAG.add_node(node_index, gate=tokens[0], trgt=trgt, id=node_index)
                list_root_nodes.append(DAG.nodes[node_index])

        elif tokens[0] in ["Cbit"]:
            pass

        else:
            raise Exception(f"Error Happened : Not recognized instruction -> {tokens}")

        node_index+=1

    DAG.add_edges_from(list_nodes_connection)

    return {"DAG": DAG, "roots": list_root_nodes}


def get_parent_from_node(DAG, node, depth):
    '''
        function to return ancestors in depth steps from the current node
    '''
    parents = collections.defaultdict(list)
    parents[0] = [node]

    for i in range(depth):
        if i in parents.keys() and len(parents[i]):
            for j in parents[i]:
                parents[i+1].extend(list(DAG.predecessors(j)))

    list_parents = list(itertools.chain.from_iterable(parents.values()))
    list_parents.remove(node)

    return list_parents


def get_children_from_node(DAG, node, depth):
    '''
        DAG의 특정 노드로 부터 depth 만큼 아래의 노드 return
        Extended Set E 생성하기 위해 필요한 함수
    '''

    children = collections.defaultdict(list)
    children[0] = [node["id"]]

    for i in range(depth):
        if i in children.keys() and len(children[i]):
            for j in children[i]:
                children[i+1].extend(list(DAG.successors(j)))

    list_children = list(itertools.chain.from_iterable(children.values()))
    list_children.remove(node["id"])

    return list_children
