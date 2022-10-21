# How to use *ftsynthesis*
- This document provides how to use the package.
- This document describes the user api and how to call it with arguments


## Main Module and API function
- main module : *ftsynthesis*
- main function : *synthesize*
- syntax:
```
# import the package
import ftsynthesis.ftsynthesis as synthesizer
	
# function call
synthesizer.synthesize(protocol, qubit_layout, synthesis_option=option, qubit_table=qubit_mapping)
```
- output
```
{
	"analysis": {
		"CNOT Overhead": ..,
		"Circuit Depth": ..,
		"Function List": ..,
		"Interaction": ..,
		"Qubit": ..
	},
	"qchip" : ..,
	"system_code": {
		"circuit": ..,
		"initial_mapping": ..,
		"final_mapping": ..
	}
}
```

### Items of output
- *analysis* : statistics of the resulting circuit (circuit size, component quantum gates etc.)
- *qchip* : input qubit layout information
- *system\_code* : the circuit (gate scheduling), the initial_mapping and final mapping
		

## Arguments of *ftsynthesis*
### 1. Fault-Tolerant Protocol
- It should be provided as a quantum assembly code format (.qasmf).
- Note that in the directory [**tests/DB-QASM**](../tests/DB-QASM), you can see the sample files.
- When you write a qasm file, there is a naming rule as follws
- Example:
```
# Logical CNOT gate protocol of [[7, 1, 3]] Steane code
Qubit LQ1-data0
..
Qubit LQ1-data6
Qubit LQ2-data0
..
Qubit LQ2-data6
CNOT LQ1-data0,LQ2-data0
..
CNOT LQ1-data6,LQ2-data6
```

#### Naming Rule ####
- The data qubit that holds the data in a logical qubit should be named as having "data" (e.g., *data\_i*)
- The magic qubit that holds the data in a magic state should be named as having "magic" (e.g., *magic\_j*)  

### 2. Qubit layout
- It is the qubit connectivity information and should be provided as a json format file.
- We provided a module *layout\_generator* that generates a regular qubit lattice of a given size (*height* and *width*)
- How to use the module is provided below.
- Example: 
```
{
	...
	"dimension":{"height":7, "width":7},
	"qubit_connectivity":{
		"0":[7, 1],
		"1":[8, 0, 2],
	...
}
```
### 3. Synthesis option
- It is a information for the circuit synthesis.
- Example:
```
synthesis_option={"iteration": 1, 
		"moveback": True, 
		"allowable_data_interaction" : 0,
		"optimal_criterion" : "circuit_depth", 
		"cost_function": "lap", "lap_depth": 5, 
		"decay_factor": 0.1,
		"extended_set_weight": 0.5,
		"initial_mapping_option": "periodic_random"}
```

#### Description of the option items
- **iteration** : the number of SABRE iterations (positive integer 1,2, ..)
- **moveback** : the moveback operation (*True* or *False*)
- **allowable\_data\_interaction** : the upper bound for swap gates between data-type qubits
- **optimal\_criterion** : criterion to determine the optimality of a circuit (*circuit\_depth* or *number\_gates*)
- **cost\_function** : cost function employed in the circuit synthesis algorithm (*nnc* or *lap*)
	- *nnc* : cost evaluation based on *front layer* only.
	- *lap* : cost evaluation based on *front layer* and *extended set* ahead of front layer
- **lap\_depth** : in case of lap, the depth of the extended set from front layer (positive integer)
- **decay\_factor** : in case of lap, factor to control the parallelism of swap gates (positive real number: 0 ~ 1)
- **extended\_set\_weight** : in case of lap, the weight how much the cost of the extended set is involved in the cost (positive real number: 0 ~ 1)
- **initial\_mapping\_option** : option for the initial random qubit mapping how to generate it (*random*, *periodic_random*)
	- *random* : make a initial mapping completely randomly
	- *periodic_random* : allocate random number periodically on a qubit layout

### 4. Qubit Mapping
- To perform the circuit synthesis for a non-pivot protocol, the fixed position of the data (and magic) qubits should be provided.
- It is the json formed data.
- For 2-qubit gates including T gate, we need to extend the qubit layout by merging two logical 1-qubit layouts. This is done by following procedures.
	1. call the module to generate an extended qubit layout
	```
	layout_generator.generate_regular_qchip_architecture(job_dir, extended_layout_size)
	```
	2. call the module to merge two logical single-qubit layouts and arrange the qubits properly. (How to call the module is described below)
	```
	extended_layout = util.merge_qubit_layout(inverse_qubit_table_LQ1, inverse_qubit_table_LQ2, 
						direction=neighbor_direction, layout_size=data_best_layout_size)
	```
## How to call Main Module
- It should be called with the arguments (protocol, qubit layout and synthesis option). Please see the sample codes for [Steane Code](../tests/test_steane.py) or [Golay Code](../tests/test_golay.py).
- For the circuit synthesis over multiple protocols, you need to see the below figure. ![concept](hierarchical_FT_circuit_synthesis.png)


## How to use the utility functions
### 1. *layout\_generator.generate\_regular\_qchip\_architecture*
- function to generate a regular qubit layout (All-to-All, 1-D, 2-D)
- syntax
```
# size of a qubit layout
layout_size = {"height": height, "width": width}
	
# call the module to generate a qubit layout
qchip1_layout = layout_generator.generate_regular_qchip_architecture(job_dir, layout_size, architecture=2)
```
- arguments
	- *job\_dir* : the directory where the function saves the resulting layout file (.json)
	- *layout\_size* : the size of the qubit layout
	- *architecture* : the dimension of the qubit layout (*0*, *1*, *2*)
		- 0: all-to-all connection 
		- 1: one-dimensional lattice
		- 2: two-dimensional lattice

- output (python dictionary type data)
	- path for file : path for the file based on the input *job\_dir*
	- qchip\_architecture : the dictionary data that includes a list containing the connected qubit index for a pivot qubit (see the example of qubit layout above)
```
{"result_file": full_path_device, "qubit_connectivity": qchip_architecture}
```

### 2. *util.merge\_qubit\_layout*
- function to merge two qubit layouts for an extended layout and to allocate the qubits in small layouts onto an extended layout
- syntax
```
extended_layout = util.merge_qubit_layout(inverse_qubit_table_1, inverse_qubit_table_2, 
					direction=neighbor_direction, layout_size=data_best_layout_size)
```
- arguments
	- *inverse\_qubit\_table\_1* : inverse of the qubit mapping of a logical qubit 1 -> {physical qubit index : logical qubit}
	- *inverse\_qubit\_table\_2* : inverse of the qubit mapping of a logical qubit 2 -> {physical qubit index : logical qubit}
	- *direction* : relative direction between two logical qubits (*vertical* or *horizon*)
	- *layout\_size* : the size of a single-qubit layout (NOT an extended layout) 

- outout (qubit mapping in the extended qubit layout)
```
extended layout = {
	'LQ1-checkup0': 61,
	'LQ1-data0': 87,
	'LQ1-data1': 34,
	...
	'LQ2-checkup0': 68,
	'LQ2-data0': 94,
	'LQ2-data1': 41,
	...
}		
```

### 3. *util.checkup\_fault\_tolerance*
- function to check the fault-tolerance of the resulting circuit (called in [*test.py*](../tests/test.py))
- syntax
```
util.checkup_fault_tolerance(system_code, extended_layout_size, write_file=True)
```
- arguments
	- *system\_code* : system code that includes the circuit, the initial qubit mapping and the final mapping
	- *extended\_layout\_size* : the size of the extended qubit layout
	- *write\_file* : flag whether writing the result to a file or not

- output
	- the full snapshots of the circuit with checking whether data qubits have interaction or not
 
