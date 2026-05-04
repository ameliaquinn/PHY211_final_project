from ..main import make_phases, plot_results

import numpy as np
from matplotlib import pyplot as plt

def test_make_phases():
    number_of_phases = 20
    phases, individual_phases = make_phases(number_of_phases)
    assert len(individual_phases) == number_of_phases