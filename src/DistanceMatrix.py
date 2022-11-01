# -*-coding:utf-8-*-

# This code is part of ftsynthesis
# (fault-tolerant quantum circuit synthesis for fault-tolerant quantum protocols)
#
# Copyright 2022 ETRI
#
# This code is licensed under the BSD-3-Clause.

'''
    module to compute the distance matrix
'''

import collections
import math
import itertools


def calculate_swap_matrix(qchip_data, target_criterion):
    '''
        function to calculate a swap cost (time, fidelity) between two adjacent qubits
        args : cnot matrix
    '''
    qchip_size = len(qchip_data.get("qubit_connectivity"))
    connectivity_matrix = qchip_data.get("qubit_connectivity")

    if target_criterion == "time":
        matrix = [[0 if i==j else math.inf for i in range(qchip_size)] for j in range(qchip_size)]
        cnot_cost = qchip_data.get("cnot_gate_time")

        for i in connectivity_matrix:
            for j in connectivity_matrix[i]:
                matrix[i][j] = cnot_cost[i][j]*2 + cnot_cost[j][i]

        return matrix

    elif target_criterion == "fidelity":
        matrix = [[1.0 if i==j else 0 for i in range(qchip_size)] for j in range(qchip_size)]
        cnot_cost = qchip_data.get("cnot_error_rate")

        for i in connectivity_matrix:
            for j in connectivity_matrix[i]:
                matrix[i][j] = (1.0-cnot_cost[i][j])**2 * (1-cnot_cost[j][i])

        return matrix


def floyd_warshall(matrix, criterion):
    '''
        function for floyd warshall algorithm
    '''
    V = len(matrix)
    if not V:
        raise Exception("The input information of the graph is wrong")

    # path 찾기 위해 요구되는
    pi = [[i if matrix[i][j] not in [0, math.inf] else -1 for j in range(V)] for i in range(V)]

    if criterion in ["distance", "time"]:
        for k in range(V):
            next_matrix = [list(row) for row in matrix]
            for idx in itertools.product(range(V), range(V)):
                if matrix[idx[0]][idx[1]] > matrix[idx[0]][k] + matrix[k][idx[1]]:
                    next_matrix[idx[0]][idx[1]] = matrix[idx[0]][k] + matrix[k][idx[1]]
                    pi[idx[0]][idx[1]] = pi[k][idx[1]]

            matrix = next_matrix

    elif criterion == "fidelity":
        for k in range(V):
            next_matrix = [list(row) for row in matrix]
            for idx in itertools.product(range(V), range(V)):
                if matrix[idx[0]][idx[1]] < matrix[idx[0]][k] * matrix[k][idx[1]]:
                    next_matrix[idx[0]][idx[1]] = matrix[idx[0]][k] * matrix[k][idx[1]]
                    pi[idx[0]][idx[1]] = pi[k][idx[1]]

            matrix = next_matrix

    return matrix, pi


def find_paths(pi, qchip_size):
    """
        function to find all the shortest path over multiple nodes
    """
    paths = collections.defaultdict(list)

    for idx in itertools.product(range(qchip_size), range(qchip_size)):
        if idx[0] == idx[1]:
            continue

        paths[(idx[0], idx[1])].extend([idx[0], idx[1]])

        while True:
            current_node = paths[(idx[0], idx[1])][1]

            if pi[idx[0]][current_node] == idx[0]:
                break

            paths[(idx[0], idx[1])].insert(1, pi[idx[0]][current_node])

    return paths


def post_processing(matrix, qchip_data, path, target_criterion):
    """
         function post processing to cancel out the swap cost
    """
    qchip_size = len(qchip_data.get("qubit_connectivity"))

    if target_criterion == "time":
        cnot_cost = qchip_data.get("cnot_gate_time")

        for idx in itertools.product(range(qchip_size), range(qchip_size)):
            if idx[0] == idx[1]:
                continue
            final_edge = path[(idx[0], idx[1])][-2:]
            matrix[idx[0]][idx[1]] -= cnot_cost[final_edge[0]][final_edge[1]] +\
                                       cnot_cost[final_edge[1]][final_edge[0]]

    elif target_criterion == "fidelity":
        cnot_cost = qchip_data.get("cnot_error_rate")

        for idx in itertools.product(range(qchip_size), range(qchip_size)):
            if idx[0] == idx[1]:
                continue
            final_edge = path[(idx[0], idx[1])][-2:]
            matrix[idx[0]][idx[1]] /= (1-cnot_cost[final_edge[0]][final_edge[1]]) *\
                                      (1-cnot_cost[final_edge[1]][final_edge[0]])

    return matrix


def generateDM(qchip_data, target_criterion):
    '''
         function to develop distance matrix
    '''
    connectivity_matrix = qchip_data.get("qubit_connectivity")
    qchip_size = len(qchip_data.get("qubit_connectivity"))

    if target_criterion == "distance":
        matrix = [[0 if i==j else math.inf for i in range(qchip_size)] for j in range(qchip_size)]

        for i in connectivity_matrix:
            for j in connectivity_matrix[i]:
                matrix[i][j] = 1

        answer_matrix, pi = floyd_warshall(matrix, target_criterion)
        paths = find_paths(pi, qchip_size)

    else:
        swap_cost_matrix = calculate_swap_matrix(qchip_data, target_criterion)

        # swap 비용 기준으로 최적 비용 행렬 계산
        matrix, pi = floyd_warshall(swap_cost_matrix, target_criterion)

        # 최적 비용 행렬 계산 하는 과정에서 함께 생성한 중간 노드 지정 행렬을 기반으로 경로 계산
        paths = find_paths(pi, qchip_size)

        # 경로의 마지막 구간을 기준으로 swap 비용 행렬에 대한 후 보정
        answer_matrix = post_processing(matrix, qchip_data, paths, target_criterion)

    return answer_matrix, paths
