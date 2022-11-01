
# -*-coding:utf-8-*-

# This code is part of ftsynthesis
# (fault-tolerant quantum circuit synthesis for fault-tolerant quantum protocols)
#
# Copyright 2022 ETRI
#
# This code is licensed under the BSD-3-Clause.

'''
    module to check up the resulting circuit
'''

import re
import globalVariable as g


def checkup_system_code(system_code, qchip):
# def checkup_system_code(system_code, qchip, **kwargs):
    """
        function to checkup of the circuit
        whether the system_code is compatible with the quantum chip (qubit connectivity)
    """
    parser = re.compile(r"[\{a-zA-Z0-9_.*\->\+}]+")
    flag_verification = True

    if isinstance(system_code, dict):
        for instructions in list(system_code.values()):
            for inst in instructions:
                tokens = parser.findall(inst)

                if tokens is None or len(tokens) == 0:
                    continue

                if tokens[0] in [g.str_gate_cnot, g.str_gate_swap, g.str_gate_cz]:
                    ctrl, trgt = map(int, tokens[1:])
                    if trgt not in qchip["qubit_connectivity"][ctrl]:
                        flag_verification = False
                        break

    elif isinstance(system_code, list):
        for inst in system_code:
            if inst[0] in [g.str_gate_cnot, g.str_gate_swap, g.str_gate_cz]:
                ctrl, trgt = map(int, inst[1:])
                if trgt not in qchip["qubit_connectivity"][ctrl]:
                    flag_verification = False
                    break

    return flag_verification

