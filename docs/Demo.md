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

1. A Logical-1 Qubit Protocol
  - Define the size of a layout
  - Generate a qubit layout (done in the sample code via calling a module [layout_generator](../tests/layout_generator.py)
  - Synthesize the Stabilizer Measurement on the qubit layout
  - Synthesize the FT Preparation of the logical zero state

## Syndrome Measurement of Golay code
