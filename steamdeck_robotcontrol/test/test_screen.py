from ..screen import *

def test_matching_result():
    match ContinueExecution.value:
        case ContinueExecution(): assert True
        case _: assert False