# -*-coding:utf-8-*-

# This code is part of ftsynthesis (fault-tolerant quantum circuit synthesis for fault-tolerant quantum protocols)
#
# Copyright 2022 ETRI
#
# This code is licensed under the BSD-3-Clause.

import io
from setuptools import find_packages, setup

setup(
	name				= "ftsynthesis",
	version				= '0.0.2',
	description			= 'fault tolerant circuit synthesis for universal fault-tolerant quantum computing based on concatenated codes',
	author 				= 'Yongsoo Hwang',
	author_email 		= 'yhwang@etri.re.kr',
	install_requires 	= ['simplejson', 'icecream', 'pandas', 'networkx', 'parse', 'progress', 'qubitmapping', 'userproperty'],
	packages 			= find_packages(),
	zip_safe 			= False,
	python_requires 	= '>=3'
	)
