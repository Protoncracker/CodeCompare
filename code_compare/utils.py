import gc
import sys
import os
from contextlib import contextmanager

@contextmanager
def suppress_output():
    with open(os.devnull, 'w') as devnull:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

@contextmanager
def gc_disabled():
    gc_enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if gc_enabled:
            gc.enable()
