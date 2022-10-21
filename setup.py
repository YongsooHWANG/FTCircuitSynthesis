
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