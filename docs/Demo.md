# How to use the sample code *test\_steane.py* and *test\_golay.py*.

## FTQC based on Steane code 
### FT Protocols
- Syndrome Measurement : [Steane Method(PRL 78, 2252)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.78.2252)
- FT Preparation of Logical Zero State : [Goto (Sci. Rep. 6, 19578)](https://www.nature.com/articles/srep19578) 
- Magic State : [Magic State Preparation (arXiv:0504218)](https://arxiv.org/abs/quant-ph/0504218)
- T gate : [Teleportation-based (PRA 62, 052316)](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.62.052316)

Note that the quantum assembly code developed by us can be seen in the directory [tests/DB-QASM](../tests/DB-QASM)

### *test\_steane.py*
#### Flow of the circuit synthesis

1. Logical 1-Qubit Protocols
  1) Define the size of a layout
  2) Generate a qubit layout (done in the sample code via calling a module [layout_generator](../tests/layout_generator.py)
  3) Synthesize the Stabilizer Measurement on the qubit layout -> keep the position of data qubits (A)
  4) Synthesize the FT Preparation of the logical zero state
  5) Synthesize the Magic State Preparation -> keep the position of magic qubits

2. Logical 2-Qubit Protocols
  Over the relative position between two qubits (*vertical* and *horizon*) 
  1) Generate a qubit layout
  2) Synthesize the CNOT (based on the position of the data qubits (A)
  3) Synthesize the T Gate (based on the position of the data qubits (A) and magi qubits (B)


## Syndrome Measurement of Golay code
