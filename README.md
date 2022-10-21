# Fault-Tolerant Quantum Circuit Synthesis for Universal Fault-Tolerant Quantum Computing
- This project develops a quantum circuit synthesis algorithm for univeral fault-tolerant quantum computing based on concatenated codes such as [[7,1,3]] Steane code and [[25,1,7]] Golay code.
- The circuits of fault-tolerant quantum protocol should be executable in terms of locality constraint that a quantum chip has, but with retaining both the fault tolerance and the logic sequence of the protocol.

## Environment
- Language :  Python3
- OS:  Ubuntu 20.04 

Note: It does not work well on Mac OS now, but will be fixed soon.

## Prerequisites
To run the project successfully, you need to install the following packages included in "requirements.txt" beforehand.
- simplejson, icecream, pandas, networkx, parse, progress, qubitmapping, userproperty

```
pip install -r requirements.txt
```
Note that the packages *qubitmapping* and *userproperty* are developed by Y.Hwang for this project.

## Installation
We encourage installing this project by cloning the source code from GitHub server.
```
bash
git clone https://gist.github.com/PurpleBooth/109311bb0361f32d87a2
```

It also can be installed via the pip tool (a python package manager). The following command installs the project.
```
pip install ftsynthesis
```

## Usage

Please see [How To Use.md](docs/HowToUse.md) to know how to use the package.

For the sample demonstration codes for Steane code and Golay code, please see [Demo.md](docs/Demo.md).

## Authors
- Y. Hwang (ETRI, Quantum Technology Research Department), yhwang@etri.re.kr


## Reference
If you use our project for your research, we would be thankful if you referred to it by citing the following publication:
```
@article{hwang2022,
  author    = {Y. Hwang},
  title     = {Fault-Tolerant Circuit Synthesis for Universal Fault-Tolerant Quantum Computing},
  ee        = {https://arxiv.org/abs/2206.02691},
  year      = {2022},
}
```

## License
GNU GPLv3

## Acknowledgement

This work was partly supported by Institute for Information & communications Technology Promotion (IITP) grant funded by the Korea government (MSIT) (No. 2019-0-00003, Research and Development of Core Technologies for Programming, Running, Implementing and Validating of Fault-Tolerant Quantum Computing System & No.2022-0-00463, Development of a quantum repeater in optical ﬁber networks for quantum internet) and the National Research Foundation of Korea (NRF) grant funded by the Korea government (MSIT) (No. NRF-2019M3E4A1080146).


