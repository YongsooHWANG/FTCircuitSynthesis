# -*-coding:utf-8-*-

import os
import simplejson as json
import numpy as np
import itertools
import collections

def generate_regular_qchip_architecture(parent_dir, layout_size, **kwargs):
    '''
        function to make a file of qubit architecture
    '''

    qubit_connectivity = collections.defaultdict(list)
    width = layout_size["width"]
    height = layout_size["height"]
    
    qubits = width * height

    if "architecture" in kwargs:
        architecture = kwargs["architecture"]
    else:
        architecture = 2

    if architecture == 0:
        for idx in range(qubits):
            qubit_connectivity[idx] = list(range(qubits))
            qubit_connectivity[idx].remove(idx)
    
    else:    
        for idx in itertools.product(range(height), range(width)):
            _cell_idx = idx[0]*width + idx[1]
            _list_neighbor = []
            
            if not idx[0]:
                if height > 1:
                    qubit_connectivity[_cell_idx].append(_cell_idx + width)
            elif idx[0] < height - 1:
                qubit_connectivity[_cell_idx].extend([_cell_idx-width, _cell_idx+width])

            elif idx[0] == height - 1:
                qubit_connectivity[_cell_idx].append(_cell_idx-width)

            if not idx[1]:
                if width > 1:
                    qubit_connectivity[_cell_idx].append(_cell_idx+1)
            elif idx[1] < width - 1:
                qubit_connectivity[_cell_idx].extend([_cell_idx-1, _cell_idx+1])

            elif idx[1] == width-1:
                qubit_connectivity[_cell_idx].append(_cell_idx-1)

    file_device = "".join(["file_qchip_{}x{}.json".format(height, width)])
    qchip_architecture = {"qubit_connectivity": qubit_connectivity, "device_name": file_device,
                          "dimension": {"height": height, "width": width}}

    full_path_device = os.path.join(parent_dir, file_device)


    with open(full_path_device, "w") as f:
        json.dump(qchip_architecture, f, sort_keys=True, indent=4, separators=(',', ':'))

    return {"result_file": full_path_device, "qubit_connectivity": qchip_architecture}
