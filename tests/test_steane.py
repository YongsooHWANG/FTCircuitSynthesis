
# -*-coding:utf-8-*-

# This code is part of ftsynthesis
# (fault-tolerant quantum circuit synthesis for fault-tolerant quantum protocols)
#
# Copyright 2022 ETRI
#
# This code is licensed under the BSD-3-Clause.
'''
    module for run a sample (steane code)
'''

import os
import sys
import math
import time
import collections
from pprint import pprint

import simplejson as json
from icecream import ic

# user defined library
import layout_generator
import util

sys.path.insert(0, "../src")
import ftsynthesis as synthesizer

# code
code = "steane"

# directory for input data
directory_mother_qasmf = "DB-QASM"
directory_code_qasmf = os.path.join(directory_mother_qasmf, code)

# directory for output (mother directory)
directory_mother_jobs = "DB-Jobs"
if not os.path.exists(directory_mother_jobs):
    os.mkdir(directory_mother_jobs)

collection_protocol_performance = collections.defaultdict(list)

# stabilizer measure
stabilizer_measure = "Stabilizer_Measure_steaneEC"

print(f"stabilizer measurement circuit : {stabilizer_measure}")

# files for fault-tolerant protocols (in qasm)
ftqc_protocol = {k: "".join([os.path.join(directory_code_qasmf, k), ".qasmf"])
                 for k in [stabilizer_measure, "CNOT", "Prepare_Magic_State",
                           "T", "PrepZ"]}

synthesis_result = {}

# time information for job id
now = time.localtime()
current_time = f"{now.tm_year}{now.tm_mon}{now.tm_mday}{now.tm_hour}{now.tm_min}{now.tm_sec}"
job_id = current_time

# job directory in the mother directory (DB-Jobs)
job_dir = os.path.join(directory_mother_jobs, job_id)
if not os.path.exists(job_dir):
    os.mkdir(job_dir)

# the options for the synthesis task
synthesis_option={"iteration": 1,
                  "moveback": True,
                  "allowable_data_interaction" : 0,
                  "optimal_criterion" : "number_gates",
                  "cost_function": "lap",
                  "lap_depth": 5,
                  "decay_factor": 0.1,
                  "extended_set_weight": 0.5,
                  "allow_swap" : True,
                  "initial_mapping_option": "periodic_random"}

# reference data for finding an optimal circuit
data_best_logical_qubit_configuration = None
data_best_kq = math.inf
data_best_code = None
data_best_layout_size = {"height": None, "width": None}
data_best_system_code = None
best_kq = math.inf

# synthesis for syndrome measurement
protocol = stabilizer_measure
print("===============")
print(f" protocol : {protocol}")
print("===============")

# iteration over various 2-dimensional qubit layout
# for size in [(5, 6), (5, 7), (5, 8), (6, 6), (6, 7), (6, 8), (7, 7), (7, 8)]:
for size in [(7, 7)]:
    height, width = size[:]

    print(f"the size of layout = {height}x{width}")
    layout_size = {"height": height, "width": width}

    # develop a qubit layout (2-d)
    qchip1_layout = layout_generator.generate_regular_qchip_architecture(job_dir,
                                                            layout_size, architecture=2)
    path_qchip1 = qchip1_layout.get("result_file")

    # synthesis result
    synthesis_result[stabilizer_measure] = synthesizer.synthesize(ftqc_protocol[stabilizer_measure],
                                                                    path_qchip1,
                                                                    synthesis_option=synthesis_option)

    ic(synthesis_result[stabilizer_measure])
    data_qubit_mapping_table = synthesis_result[stabilizer_measure]["system_code"]["initial_mapping"]

    circuit_depth = synthesis_result[stabilizer_measure]["analysis"]["Circuit Depth"]
    qubits = synthesis_result[stabilizer_measure]["analysis"]["Qubit"]["Qubit"]
    collection_protocol_performance[stabilizer_measure].append(synthesis_result[stabilizer_measure])
    total_gates = sum(list(synthesis_result[stabilizer_measure]["analysis"]["Function List"].values()))

    print(f"Layout Size = {height}x{width}")
    print(f"Circuit Depth = {circuit_depth}")

    kq = circuit_depth * qubits
    if kq < data_best_kq:
        data_best_kq = kq
        data_best_logical_qubit_configuration = data_qubit_mapping_table
        data_best_code = stabilizer_measure
        data_best_layout_size.update({"height": height, "width": width})
        data_best_system_code = synthesis_result[stabilizer_measure]["system_code"]
        data_best_qchip_layout = qchip1_layout

print("Minimal Circuit for Syndrome Measure:")
pprint(synthesis_result[stabilizer_measure])

print("Best Circuit for today is ")
print(f" - Layout Size : {data_best_layout_size}")
print(f" - KQ : {data_best_kq}")
print(f" - Total Gates = {total_gates}")

print(" - Qubit Layout : ")
util.display_qubit_mapping(data_best_logical_qubit_configuration,
                           data_best_layout_size)
util.checkup_fault_tolerance(data_best_system_code,
                             data_best_layout_size,
                             write_file=True)

# preparation of logical zero state
table_data_qubits = {k: v for k, v in data_best_logical_qubit_configuration.items()
                    if "data" in k}
pprint(table_data_qubits)

# Encoder
protocol = "PrepZ"
print("===============")
print(f" protocol : {protocol}")
print("===============")

synthesis_result[protocol] = synthesizer.synthesize(ftqc_protocol[protocol],
                                                    path_qchip1,
                                                    synthesis_option=synthesis_option,
                                                    qubit_table=table_data_qubits)

collection_protocol_performance[protocol].append(synthesis_result[protocol])
util.checkup_fault_tolerance(synthesis_result[protocol]["system_code"],
                             data_best_layout_size,
                             write_file=True)

protocol = "Prepare_Magic_State"
print("===============")
print(f" protocol : {protocol}")
print("===============")

synthesis_option["moveback"] = False
synthesis_result[protocol] = synthesizer.synthesize(ftqc_protocol[protocol],
                                                    path_qchip1,
                                                    synthesis_option=synthesis_option)

collection_protocol_performance[protocol].append(synthesis_result[protocol])

# qubit mapping table for magic state
magic_qubit_mapping_table = synthesis_result[protocol]["system_code"]["final_mapping"]
util.checkup_fault_tolerance(synthesis_result[protocol]["system_code"],
                             data_best_layout_size,
                             write_file=True)

# circuit synthesis over the relative directions of qubits
for neighbor_direction in ["vertical", "horizon"]:
    # doubling the qubit layout with the chosen direction (horizon or vertical)
    if neighbor_direction == "vertical":
        extended_layout_size = {"height": data_best_layout_size["height"]*2,
                                "width": data_best_layout_size["width"]}
    elif neighbor_direction == "horizon":
        extended_layout_size = {"height": data_best_layout_size["height"],
                                "width": data_best_layout_size["width"]*2}

    # extended qubit layout (vertically, horizontally)
    qchip2_layout = layout_generator.generate_regular_qchip_architecture(job_dir,
                                                                    extended_layout_size)
    path_qchip_extended_vertical = qchip2_layout["result_file"]

    # logical CNOT circuit
    protocol = "CNOT"
    print("===============")
    print(f" protocol : {protocol}")
    print("===============")

    # qubit mapping for each logical qubit with a logical qubit index LQ1 or LQ2
    inverse_qubit_table_LQ1 = {v: "-".join(["LQ1", k])
                              for k, v in data_best_logical_qubit_configuration.items()}
    inverse_qubit_table_LQ2 = {v: "-".join(["LQ2", k])
                              for k, v in data_best_logical_qubit_configuration.items()}

    # generate an extended qubit by merging two qubit layouts
    extended_layout = util.merge_qubit_layout(inverse_qubit_table_LQ1,
                                              inverse_qubit_table_LQ2,
                                              direction=neighbor_direction,
                                              layout_size=data_best_layout_size)

    print("extended layout = ")
    pprint(extended_layout)
    util.display_qubit_mapping(extended_layout, extended_layout_size)

    synthesis_option["moveback"] = True
    revised_protocol_name = f"{protocol}-{neighbor_direction}"
    synthesis_result[revised_protocol_name] = synthesizer.synthesize(ftqc_protocol[protocol],
                                                            path_qchip_extended_vertical,
                                                            synthesis_option=synthesis_option,
                                                            qubit_table=extended_layout)

    collection_protocol_performance[revised_protocol_name].append(synthesis_result[revised_protocol_name])
    util.checkup_fault_tolerance(synthesis_result[revised_protocol_name]["system_code"],
                                 extended_layout_size,
                                 write_file=True)

    # logical T gates (data - magic, magic - data)
    protocol = "T"
    print("===============")
    print(f" protocol : {protocol}")
    print("===============")

    # data 2 magic
    # for example, horizontally data(left) magic(right), vertically data(up) and magic(down)
    inverse_data_qubit_table = {v: "-".join(["LQ1", k])
                               for k, v in data_best_logical_qubit_configuration.items()}
    inverse_magic_qubit_table = {v : "-".join(["LQ2", k.replace("data", "magic")])
                                 if "data" in k
                                 else "-".join(["LQ2", k]) for k, v in magic_qubit_mapping_table.items()}

    extended_layout = util.merge_qubit_layout(inverse_data_qubit_table,
                                              inverse_magic_qubit_table,
                                              direction=neighbor_direction,
                                              layout_size=data_best_layout_size)

    util.display_qubit_mapping(extended_layout, extended_layout_size)
    revised_protocol_name = f"{protocol}-{neighbor_direction}-d2m"
    synthesis_result[revised_protocol_name] = synthesizer.synthesize(ftqc_protocol[protocol],
                                                        path_qchip_extended_vertical,
                                                        synthesis_option=synthesis_option,
                                                        qubit_table=extended_layout)

    collection_protocol_performance[revised_protocol_name].append(synthesis_result[revised_protocol_name])
    util.checkup_fault_tolerance(synthesis_result[revised_protocol_name]["system_code"],
                                 extended_layout_size, write_file=True)

    # magic 2 data
    # for example, horizontally data(right) magic(left), vertically data(down) and magic(up)
    inverse_data_qubit_table = {v: "-".join(["LQ1", k])
                                for k, v in data_best_logical_qubit_configuration.items()}
    inverse_magic_qubit_table = {v : "-".join(["LQ2", k.replace("data", "magic")])
                                 if "data" in k
                                 else "-".join(["LQ2", k])
                                 for k, v in magic_qubit_mapping_table.items()}

    extended_layout = util.merge_qubit_layout(inverse_magic_qubit_table,
                                              inverse_data_qubit_table,
                                              direction=neighbor_direction,
                                              layout_size=data_best_layout_size)

    util.display_qubit_mapping(extended_layout, extended_layout_size)
    revised_protocol_name = f"{protocol}-{neighbor_direction}-m2d"
    synthesis_result[revised_protocol_name] = synthesizer.synthesize(ftqc_protocol[protocol],
                                                        path_qchip_extended_vertical,
                                                        synthesis_option=synthesis_option,
                                                        qubit_table=extended_layout)

    collection_protocol_performance[revised_protocol_name].append(synthesis_result[revised_protocol_name])
    util.checkup_fault_tolerance(synthesis_result[revised_protocol_name]["system_code"],
                                 extended_layout_size,
                                 write_file=True)

if __name__ == "__main__":
    # write the circuit synthesis result data
    file_performance = f"protocol_performance-{code}-{job_id}.json"
    path_performance = os.path.join(job_dir, file_performance)

    with open(path_performance, "a", encoding="utf-8") as outfile:
        json.dump(collection_protocol_performance, outfile, sort_keys=True, indent=4, separators=(',', ' : '))
