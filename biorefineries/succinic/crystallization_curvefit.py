#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# Bioindustrial-Park: BioSTEAM's Premier Biorefinery Models and Results
# Copyright (C) 2021-, Sarang Bhagwat <sarangb2@illinois.edu>
#
# This module is under the UIUC open-source license. See
# github.com/BioSTEAMDevelopmentGroup/biosteam/blob/master/LICENSE.txt
# for license details.

This module is a modified implementation of modules from the following:
[1]	Bhagwat et al., Sustainable Production of Acrylic Acid via 3-Hydroxypropionic Acid from Lignocellulosic Biomass. ACS Sustainable Chem. Eng. 2021, 9 (49), 16659–16669. https://doi.org/10.1021/acssuschemeng.1c05441
[2]	Li et al., Sustainable Lactic Acid Production from Lignocellulosic Biomass. ACS Sustainable Chem. Eng. 2021, 9 (3), 1341–1351. https://doi.org/10.1021/acssuschemeng.0c08055
[3]	Cortes-Peña et al., BioSTEAM: A Fast and Flexible Platform for the Design, Simulation, and Techno-Economic Analysis of Biorefineries under Uncertainty. ACS Sustainable Chem. Eng. 2020, 8 (8), 3302–3310. https://doi.org/10.1021/acssuschemeng.9b07040

@author: sarangbhagwat
"""

import numpy as np

log = np.log

# Data from Prof. Vijay Singh's group
C0s = [250,	175,	100] # g/L
Cts = [111.4,	106,	93.6] # g/L

# Fit
log_C0s = np.log(C0s)
A, B = np.polyfit(log_C0s, Cts, 1)

Ct_given_C0 = lambda C0: A*log(C0) + B

# Plot
plot = False
if plot:
    from matplotlib import pyplot as plt
    C0s_fed = np.linspace(100, 250, 50)
    Cts_pred = [Ct_given_C0(C0) for C0 in C0s_fed]
    plt.plot(C0s_fed, Cts_pred)
    plt.plot(C0s, Cts)
    plt.show()
    