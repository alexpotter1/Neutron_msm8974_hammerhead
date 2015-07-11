#!/usr/bin/env python

import subprocess

pObject = subprocess.Popen("command -v python3", shell=True, stdin=subprocess.PIPE,
stdout=subprocess.PIPE, stderr=subprocess.PIPE)

output, err = pObject.communicate()
exitcode = pObject.returncode

if not "python3" in output:
    subprocess.call("sudo apt-get install python3", shell=True)
else:
    subprocess.call("python3 build/buildDaemon.py", shell=True)
