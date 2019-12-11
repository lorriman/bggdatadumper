'''
=========
Installer
=========

Script to install librariess we use. 
You should invoke your py environment before running this.
'''

from subprocess import call

cmds=[
    'python3 -m pip install beautifulsoup4',
    'python3 -m pip install defusedxml',
    'python3 -m pip install jsonpickle',
    'python3 -m pip install lxml',
    'python3 -m pip install simplejson',
    'python3 -m pip install xmlutils',
    'python3 -m pip install urllib3'
]

for c in cmds:
    call(c,shell=True)