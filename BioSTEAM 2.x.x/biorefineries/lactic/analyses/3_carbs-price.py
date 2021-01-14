#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# BioSTEAM: The Biorefinery Simulation and Techno-Economic Analysis Modules
# Copyright (C) 2020, Yoel Cortes-Pena <yoelcortes@gmail.com>
# Bioindustrial-Park: BioSTEAM's Premier Biorefinery Models and Results
# Copyright (C) 2020, Yalin Li <yalinli2@illinois.edu>,
# Sarang Bhagwat <sarangb2@illinois.edu>, and Yoel Cortes-Pena (this biorefinery)
# 
# This module is under the UIUC open-source license. See 
# github.com/BioSTEAMDevelopmentGroup/biosteam/blob/master/LICENSE.txt
# for license details.


# %% 

# =============================================================================
# Setup
# =============================================================================

import numpy as np
import pandas as pd
import biosteam as bst
from biosteam.utils import TicToc

_kg_per_ton = 907.18474
_feedstock_factor = _kg_per_ton / 0.8


# %%

# =============================================================================
# Model to evalute system across feedstock carbohydate content at different
# feedstock price metrics
# =============================================================================

def set_carbs(carbs_content, feedstock):
    carbs = ('Glucan', 'Xylan', 'Arabinan', 'Galactan', 'Mannan')
    dry_mass = feedstock.F_mass.copy() - feedstock.imass[('H2O',)].copy()
    old_carbs_mass_total = feedstock.imass[carbs].sum().copy()
    ratio = feedstock.get_normalized_mass(carbs)
    new_carbs_mass = dry_mass * carbs_content * ratio
    feedstock.set_flow(new_carbs_mass, 'kg/hr', carbs)
    mass_diff = new_carbs_mass.sum() - old_carbs_mass_total
    feedstock.imass['Extractives'] -= mass_diff
    if any(feedstock.mass < 0):
        raise ValueError(f'Carbohydrate content of {carbs_content*100:.1f} dw% is infeasible')

prices = np.arange(0, 210, 10)


# %%

# =============================================================================
# Evaluate across feedstock price and carbohydrate content
# =============================================================================

# Initiate a timer
timer = TicToc('timer')
timer.tic()
run_number = 0

TEA_carbs = []
TEA_prices = []
titers = []
MPSPs = []
NPVs = []
GWPs = []
FECs = []

# Configuration 2
from biorefineries.lactic import system_shf as shf
shf.simulate_and_print()

carb_contents1 = np.arange(0.25, 0.59, 0.01)
carb_contents1 = carb_contents1.tolist() + [0.589]
shf.R301.allow_dilution = False
shf.R301.allow_concentration = True
shf.R301.mode = 'Batch'
shf.R301.target_titer = 97.5

# Using two loops are not optimal, can potentially use Model and Metric to speed up
bst.speed_up()
for i in carb_contents1:
    set_carbs(i, shf.feedstock)
    shf.lactic_sys.simulate()
    titers.append(shf.R301.effluent_titer)
    GWPs.append(shf.get_GWP())
    FECs.append(shf.get_FEC())
    for j in prices:
        TEA_carbs.append(i)
        TEA_prices.append(j)
        shf.feedstock.price = j / _feedstock_factor
        shf.lactic_acid.price = 0
        for m in range(3):
            MPSP = shf.lactic_acid.price = \
                shf.lactic_tea.solve_price(shf.lactic_acid)
        MPSPs.append(MPSP)
        NPVs.append(shf.lactic_tea.NPV)
    run_number += 1
    print(f'Run #{run_number}: {timer.elapsed_time:.0f} sec')

# Then concentration needed to get to the baseline titer
from biorefineries.lactic import system_sscf as sscf
sscf.simulate_and_print()

carb_contents2 = np.arange(0.59, 0.701, 0.01).tolist()
sscf.R301.allow_dilution = True
sscf.R301.allow_concentration = False
sscf.R301.target_titer = 97.5

bst.speed_up()
for i in carb_contents2:
    set_carbs(i, sscf.feedstock)
    sscf.lactic_sys.simulate()
    titers.append(sscf.R301.effluent_titer)
    GWPs.append(sscf.get_GWP())
    FECs.append(sscf.get_FEC())
    for j in prices:
        TEA_carbs.append(i)
        TEA_prices.append(j)
        sscf.feedstock.price = j / _feedstock_factor
        sscf.lactic_acid.price = 0
        for m in range(3):
            MPSP = sscf.lactic_acid.price = \
                sscf.lactic_tea.solve_price(sscf.lactic_acid)
        MPSPs.append(MPSP)
        NPVs.append(sscf.lactic_tea.NPV)
    run_number += 1
    print(f'Run #{run_number}: {timer.elapsed_time:.0f} sec')

TEA_plot_data = pd.DataFrame({
    'Carbohydrate content [dw%]': TEA_carbs,
    'Price [$/dry-ton]': TEA_prices,
    'MPSP [$/kg]': MPSPs,
    'NPVs [$]': NPVs
    })

LCA_plot_data = pd.DataFrame({
    'Carbohydrate content [dw%]': carb_contents1+carb_contents2,
    'Titers [g/L]': titers,
    'GWP [kg CO2-eq/kg]': GWPs,
    'FEC [MJ/kg]': FECs
    })

# '''Output to Excel'''
# with pd.ExcelWriter('3_carbs-price.xlsx') as writer:
#     TEA_plot_data.to_excel(writer, sheet_name='TEA')
#     LCA_plot_data.to_excel(writer, sheet_name='LCA')

time = timer.elapsed_time / 60
print(f'\nSimulation time for {run_number} runs is: {time:.1f} min')












