# How to use the sample code *test\_steane.py* and *test\_golay.py*.

## FTQC based on Steane code 
### Fault-Tolerant Protocols included
- Syndrome Measurement : [Steane Method(PRL 78, 2252)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.78.2252)
- FT Preparation of Logical Zero State : [Goto (Sci. Rep. 6, 19578)](https://www.nature.com/articles/srep19578) 
- Magic State Preparation : [Magic State Preparation (arXiv:0504218)](https://arxiv.org/abs/quant-ph/0504218)
- T gate : [Teleportation-based (PRA 62, 052316)](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.62.052316)

Note that the quantum assembly code developed by us can be seen in the directory [tests/DB-QASM/steane](../tests/DB-QASM/steane)

### *test\_steane.py*
#### How to execute
```
python test_steane.py
```
Note that the code includes calling the print function (*print* or *ic*). If you don't want to see all, please delete them selectively.

#### Flow of the circuit synthesis

##### Logical 1-Qubit Protocols
  1. Define the size of a layout
  2. Generate a qubit layout (done in the sample code via calling a module [layout_generator](../tests/layout_generator.py)
  3. Synthesize [Stabilizer Measurement](../tests/DB-QASM/steane/Stabilizer_Measure_steaneEC.qasmf) on the qubit layout -> keep the position of data qubits (A)
  4. Synthesize [FT Preparation of the logical zero state](../tests/DB-QASM/steane/PrepZ.qasmf)
  5. Synthesize [Magic State Preparation](../tests/DB-QASM/steane/Prepare_Magic_State.qasmf) -> keep the position of magic qubits

The snapshots of the syndrome measurement circuit are shown in the [Reference](https://arxiv.org/abs/2206.02691)

##### Logical 2-Qubit Protocols
  Over the relative position between two qubits (*vertical* and *horizon*) 
  1. Generate a qubit layout
  2. Synthesize [CNOT](../tests/DB-QASM/steane/CNOT.qasmf) (based on the position of the data qubits (A)
  3. Synthesize [T Gate](../tests/DB-QASM/steane/T.qasmf) (based on the position of the data qubits (A) and magic qubits (B)

## Syndrome Measurement of Golay code
### Fault-Tolerant Protocols included
- Syndrome Measurement : [Steane Method(PRL 78, 2252)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.78.2252)
- FT Preparation of Logical Zero State : [Paetznick and Reichardt (arXiv:1106.2190)](https://arxiv.org/abs/1106.2190) 

Note that the quantum assembly code developed by us can be seen in the directory [tests/DB-QASM/golay](../tests/DB-QASM/golay)

### *test\_golay.py*
#### How to execute
```
python test_golay.py
```
Note that the code includes calling the print function (*print* or *ic*). If you don't want to see all, please delete them selectively.

#### Flow of the circuit synthesis

##### Logical 1-Qubit Protocols
  1. Define the size of a layout
  2. Generate a qubit layout (done in the sample code via calling a module [layout_generator](../tests/layout_generator.py)
  3. Synthesize [Preparation of logical zero state (without verification)](../tests/DB-QASM/golay/prepare_zero_state.qasmf) -> keep the position of data qubits (A)
  4. Synthesize [first vertification stage](../tests/DB-QASM/golay/verification_first.qasmf)
  5. Synthesize [second verification state](../tests/DB-QASM/golay/verification_first.qasmf)
  6. Synthesize [Syndrome Measurement](../tests/DB-QASM/golay/syndrome_measurement.qasmf)

Note that the size of a layout in 1) is for a single logical qubit.

Since the verification stages compare 4 copies of logical zero states, to perform the circuit synthesis of FT preparation of logical zero state, we need the extended layout of size $2m\times 2n$ assuming that the size of a single logical qubit is $m\times n$.
