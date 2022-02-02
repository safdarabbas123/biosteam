#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# BioSTEAM: The Biorefinery Simulation and Techno-Economic Analysis Modules
# Copyright (C) 2020-2021, Yoel Cortes-Pena <yoelcortes@gmail.com>
# Bioindustrial-Park: BioSTEAM's Premier Biorefinery Models and Results
# Copyright (C) 2021, Yalin Li <yalinli2@illinois.edu>
#
# Part of this module is based on the lactic and HP biorefineries:
# https://github.com/BioSTEAMDevelopmentGroup/Bioindustrial-Park/tree/master/BioSTEAM%202.x.x/biorefineries/
#
# This module is under the UIUC open-source license. See
# github.com/BioSTEAMDevelopmentGroup/biosteam/blob/master/LICENSE.txt
# for license details.


import thermosteam as tmo

__all__ = ('get_cs_GWP',)


def get_cs_GWP(lca_stream, flowsheet, ratio):
    chems = lca_stream.chemicals
    # 100-year global warming potential (GWP) in kg CO2-eq/kg dry material,
    # all data from GREET 2020
    GWP_CFs = {
        'NH4OH': 2.64 * chems.NH3.MW/chems.NH4OH.MW,
        'CSL': 1.55,
        'CH4': 0.33, # NA NG from shale and conventional recovery
        'Cellulase': 2.24, # enzyme
        'Lime': 1.29 * 56.0774/74.093, # 1.29 is for CaO, need to convert to those of Ca(OH)2
        'NaOH': 2.11,
        'H2SO4': 0.04344,
        'Denaturant': 0.84, # gasoline blendstock from crude oil for use in US refineries
        # CFs for NaOCl, citric acid, and bisulfite from ecoinvent 3.7.1,
        # allocation at the point of substitution
        # Market for sodium hypochlorite, without water, in 15% solution state, RoW
        'NaOCl': 2.5165*0.125, # converted to 12.5 wt% solution (15 vol%)
        # Market for citric acid, GLO
        'CitricAcid': 5.9272,
        # Sodium hydrogen sulfite production, RoW
        'Bisulfite': 1.3065*0.38, # converted to 38% solution
        # Biogenic-CO2 should not be included
        # 'CO2': 1,
        # 'Ethanol': 1.44,
        }

    # This makes the CF into an array
    GWP_CF_array = chems.kwarray(GWP_CFs)
    GWP_CF_stream = tmo.Stream('', GWP_CF_array, units='kg/hr')

    GWP_CFs['Electricity'] = 0.48 # kg CO2-eq/kWh

    GWP_CFs['Cornstover'] = 0.096470588 * (1-0.2)

    ethanol, BT = flowsheet.stream.ethanol, flowsheet.unit.BT
    # ratio is ethanol (gal) to dry corn stover (kg)
    feedstock_GWP = GWP_CFs['Cornstover'] / ratio
    material_GWP = (GWP_CF_stream.mass*lca_stream.mass).sum()/ethanol.F_mass
    # Rate is negative when the biorefinery generates more electricity than needed
    power_GWP = BT.power_utility.rate*GWP_CFs['Electricity']/ethanol.F_mass

    return feedstock_GWP+material_GWP+power_GWP