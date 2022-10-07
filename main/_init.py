import sys
import os
import re

def _alt_proc_path():
    this_dir = os.path.abspath(__file__)
    m = re.match('(.+/)main/.+', this_dir)
    if not m:
        raise Exception('Can not find main project dir')
    project_dir = m.group(1)
    lib_dir = os.path.abspath(project_dir + '../2022-05-03-alt_proc_libs-prod/main')
    if lib_dir not in sys.path:
        sys.path.append(lib_dir)

_alt_proc_path()

