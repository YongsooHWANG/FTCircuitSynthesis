
# -*-coding:utf-8-*-

# This code is part of ftsynthesis
# (fault-tolerant quantum circuit synthesis for fault-tolerant quantum protocols)
#
# Copyright 2022 ETRI
#
# This code is licensed under the BSD-3-Clause.
'''
    module for run a sample (golay code)
'''

import os
import sys
import time
import collections

import simplejson as json
from icecream import ic
import parse

# packages developed by YH
import layout_generator
import util

sys.path.insert(0, "../ftsynthesis")
import ftsynthesis as synthesizer

# path_qec code
code = "golay"

# directory for input data
directory_mother_qasmf = "DB-QASM"
directory_code_qasmf = os.path.join(directory_mother_qasmf, code)

# directory for output (mother directory)
directory_mother_jobs = "DB-Jobs"
if not os.path.exists(directory_mother_jobs):
    os.mkdir(directory_mother_jobs)

collection_protocol_performance = collections.defaultdict(list)

synthesis_result = {}

# time information for job_id
now = time.localtime()
current_time = f"{now.tm_year}{now.tm_mon}{now.tm_mday}{now.tm_hour}{now.tm_min}{now.tm_sec}"
job_id = current_time

# job directory based on the current time
job_dir = os.path.join(directory_mother_jobs, job_id)
if not os.path.exists(job_dir):
    os.mkdir(job_dir)

# the options for the synthesis task
synthesis_option={"iteration": 1,
                  "moveback": False,
                  "allowable_data_interaction" : 0,
                  "optimal_criterion" : "number_gates",
                  "cost_function": "lap",
                  "lap_depth": 5,
                  "decay_factor": 0.1,
                  "extended_set_weight": 0.5,
                  "allow_swap" : True,
                  "initial_mapping_option": "periodic_random"}

for size in [(7, 8)]:
    height, width = size[:]
    print(f"the size of layout = {height} x {width}")
    layout_size = {"height": height, "width": width}

    ######################################################
    # generate a qubit layout (2-dimensional)
    ######################################################
    qchip1_layout = layout_generator.generate_regular_qchip_architecture(job_dir,
                                                             layout_size,
                                                             architecture=2)
    path_qchip1 = qchip1_layout["result_file"]

    ######################################################
    # protocol : Prepare Zero State (without verification)
    ######################################################
    protocol = "Prepare_Zero_State"
    path_protocol = os.path.join(directory_code_qasmf, f"{protocol}.qasmf")

    synthesis_result[protocol] = synthesizer.synthesize(path_protocol,
                                                        path_qchip1,
                                                        synthesis_option=synthesis_option)

    collection_protocol_performance[protocol].append(synthesis_result[protocol])

    ic(synthesis_result[protocol])
    circuit_depth = synthesis_result[protocol]["analysis"]["Circuit Depth"]
    qubits = synthesis_result[protocol]["analysis"]["Qubit"]["Qubit"]
    total_gates = sum(list(synthesis_result[protocol]["analysis"]["Function List"].values()))

    print(f"Layout Size = {height}x{width}")
    print(f"Circuit Depth = {circuit_depth}")
    print(f"Total Gates = {total_gates}")

    collection_protocol_performance[protocol].append(synthesis_result[protocol]["analysis"])

    table_qubit_arrangement = synthesis_result[protocol]["system_code"]["final_mapping"]
    table_data_qubit = {k: v for k, v in table_qubit_arrangement.items()
                        if "data" in k}

    ic(table_data_qubit)
    util.display_qubit_mapping(table_qubit_arrangement, layout_size)

    ######################################################
    # generate an vertically extended qubit layout
    ######################################################
    direction = "vertical"
    extended_layout_size_vertical = {"height": layout_size["height"]*2,
                                     "width": layout_size["width"]}

    qchip2_layout = layout_generator.generate_regular_qchip_architecture(job_dir,
                                                           extended_layout_size_vertical)
    path_qchip_extended_vertical = qchip2_layout["result_file"]

    inverse_qubit_table_LQ1 = {v: "-".join(["LQ1", k])
                               for k, v in table_qubit_arrangement.items()}
    inverse_qubit_table_LQ2 = {v: "-".join(["LQ2", k.replace("data", "ancilla")])
                               for k, v in table_qubit_arrangement.items()}

    # merge two qubit layouts and allocate the qubits on that
    extended_layout = util.merge_qubit_layout(inverse_qubit_table_LQ1,
                                              inverse_qubit_table_LQ2,
                                              direction=direction,
                                              layout_size=layout_size)

    util.display_qubit_mapping(extended_layout, extended_layout_size_vertical)

    ######################################################
    # protocol : Verification First Step
    ######################################################
    protocol = "Verification_First"
    path_protocol = os.path.join(directory_code_qasmf, f"{protocol}.qasmf")

    synthesis_result[protocol] = synthesizer.synthesize(path_protocol,
                                                        path_qchip_extended_vertical,
                                                        synthesis_option=synthesis_option,
                                                        qubit_table=extended_layout)

    collection_protocol_performance[protocol].append(synthesis_result[protocol])

    print("circuit for the verification first step")
    ic(synthesis_result[protocol])
    util.display_qubit_mapping(synthesis_result[protocol]["system_code"]["final_mapping"],
                               extended_layout_size_vertical)

    table_qubit_arrangement_after_checkup1 = \
            synthesis_result[protocol]["system_code"]["final_mapping"]

    ######################################################
    # generate an horizontally extended qubit layout
    ######################################################
    direction = "horizon"
    extended_layout_size_full = {"height": layout_size["height"]*2,
                                 "width": layout_size["width"]*2}
    qchip2_layout = layout_generator.generate_regular_qchip_architecture(job_dir,
                                                                extended_layout_size_full)
    path_qchip_extended_full = qchip2_layout["result_file"]

    inverse_qubit_table_LQ1 = {v: k for k, v in table_qubit_arrangement_after_checkup1.items()
                               if "LQ1" in k}
    inverse_qubit_table_LQ2 = {v: k.replace("LQ1", "LQ2").replace("data", "ancilla")
                               for v, k in inverse_qubit_table_LQ1.items()}

    # merge two qubit layouts and allocate the qubits on that
    extended_layout = util.merge_qubit_layout(inverse_qubit_table_LQ1,
                                              inverse_qubit_table_LQ2,
                                              direction=direction,
                                              layout_size=extended_layout_size_vertical)

    ic(extended_layout)
    util.display_qubit_mapping(extended_layout, extended_layout_size_full)

    ######################################################
    # protocol : Verification Second Step
    ######################################################
    protocol = "Verification_Second"
    path_protocol = os.path.join(directory_code_qasmf, f"{protocol}.qasmf")

    # set the homebase for MoveBack after the verification (2nd stage)
    # please see Fig. 3 of arXiv:1106.2190
    homebase = {}
    for k, v in extended_layout.items():
        if "LQ1-data" in k:
            result = parse.compile("LQ1-{}").parse(k)
            data_qubit = result[0]
            homebase[k] = table_data_qubit[data_qubit]

    print("The position of data qubits in a logical qubit")
    ic(homebase)
    synthesis_option.update({"moveback": True,
                             "homebase": homebase})
    synthesis_result[protocol] = synthesizer.synthesize(path_protocol,
                                                        path_qchip_extended_full,
                                                        synthesis_option=synthesis_option,
                                                        qubit_table=extended_layout)

    collection_protocol_performance[protocol].append(synthesis_result[protocol])
    print("circuit for the verification second step")
    ic(synthesis_result[protocol])
    util.display_qubit_mapping(synthesis_result[protocol]["system_code"]["final_mapping"],
                               extended_layout_size_full)

    # partial syndrome measure : Z-error correction (CNOT syndrome, data)
    # logical data qubit and logical zero (or plus) state are arranged horizontally
    del synthesis_option["homebase"]

    protocol = "Stabilizer_Measure_Z_steaneEC"
    path_protocol = os.path.join(directory_code_qasmf, f"{protocol}.qasmf")

    inverse_qubit_table_LQ1 = {v: k for k, v in table_data_qubit.items()}
    inverse_qubit_table_LQ2 = {v: k.replace("data", "syndrome")
                               for k, v in table_data_qubit.items()}

    extended_layout = util.merge_qubit_layout(inverse_qubit_table_LQ1,
                                              inverse_qubit_table_LQ2,
                                              direction="vertical", layout_size=layout_size)

    synthesis_result[protocol] = synthesizer.synthesize(path_protocol,
                                                        path_qchip_extended_vertical,
                                                        synthesis_option=synthesis_option,
                                                        qubit_table=extended_layout)

    collection_protocol_performance[protocol].append(synthesis_result[protocol])

    ic(synthesis_result[protocol])
    print("Qubit Mapping after the first partial syndrome measure for Z-error: ")
    util.display_qubit_mapping(synthesis_result[protocol]["system_code"]["final_mapping"],
                               extended_layout_size_vertical)

if __name__ == "__main__":
    file_performance = f"protocol_performance-{code}-{job_id}.json"
    path_performance = os.path.join(job_dir, file_performance)

    with open(path_performance, "a", encoding="utf-8") as outfile:
        json.dump(collection_protocol_performance, outfile, sort_keys=True, indent=4, separators=(',', ' : '))
