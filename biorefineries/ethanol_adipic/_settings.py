#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Bioindustrial-Park: BioSTEAM's Premier Biorefinery Models and Results
# Copyright (C) 2020-, Yalin Li <mailto.yalin.li@gmail.com>
#
# This module is under the UIUC open-source license. See
# github.com/BioSTEAMDevelopmentGroup/biosteam/blob/master/LICENSE.txt
# for license details.

'''
References
----------
[1] Humbird et al., Process Design and Economics for Biochemical Conversion of
    Lignocellulosic Biomass to Ethanol: Dilute-Acid Pretreatment and Enzymatic
    Hydrolysis of Corn Stover; Technical Report NREL/TP-5100-47764;
    National Renewable Energy Lab (NREL), 2011.
    https://www.nrel.gov/docs/fy11osti/47764.pdf
[2] Davis et al., Process Design and Economics for the Conversion of Lignocellulosic
    Biomass to Hydrocarbon Fuels and Coproducts: 2018 Biochemical Design Case Update;
    NREL/TP-5100-71949; National Renewable Energy Lab (NREL), 2018.
    https://doi.org/10.2172/1483234
[3] Argonne National Laboratory. The Greenhouse gases, Regulated Emissions,
    and Energy use in Transportation (GREET) Model https://greet.es.anl.gov/
    (accessed Aug 25, 2020).

'''

__all__ = (
    '_feedstock_factor', 'default_costs', 'set_feedstock_price',
    'price', 'CFs'
           )


# %%

# =============================================================================
# Setup
# =============================================================================

import biosteam as bst
import thermosteam as tmo
from biorefineries.ethanol_adipic._chemicals import chems

bst.CE = 541.7 # year 2016
auom = tmo.units_of_measure.AbsoluteUnitsOfMeasure
_kg_per_ton = auom('ton').conversion_factor('kg')
_lb_per_kg = auom('kg').conversion_factor('lb')
_liter_per_gallon = auom('gal').conversion_factor('L')
_ft3_per_m3 = auom('m3').conversion_factor('ft3')
_J_per_BTU =  auom('BTU').conversion_factor('J')
_GDP_2007to2016 = 1.160
_labor_2011to2016 = 1.059

# =============================================================================
# Energy balances
# =============================================================================

_lps = bst.HeatUtility.get_heating_agent('low_pressure_steam')
_mps = bst.HeatUtility.get_heating_agent('medium_pressure_steam')
_hps = bst.HeatUtility.get_heating_agent('high_pressure_steam')

# Adjusted to LP/HP steam temperature as in ref [1]
# biosteam native mps T is lower than LP steam T in ref [1], thus adjust mps.T
_mps.T = 233 + 273.15
_hps.T = 266 + 273.15
_cooling = bst.HeatUtility.get_cooling_agent('cooling_water')
_chilled = bst.HeatUtility.get_cooling_agent('chilled_water')
_cooling.T = 28 + 273.15
_cooling.T_limit = _cooling.T + 9

# Side steam in CHP not a heat utility, thus will cause problem in TEA utility
# cost calculation if price not set to 0 here, costs for regeneration of heating
# and cooling utilities will be considered as CAPEX and OPEX of CHP and CT, respectively
for i in (_lps, _mps, _hps, _cooling, _chilled):
    i.heat_transfer_price = i.regeneration_price = 0
    i.heat_transfer_efficiency = 1

# =============================================================================
# Prices for techno-economic analysis (TEA)
# =============================================================================

# From USD/dry-ton to USD/kg in 2016$, 20% moisture content
_feedstock_factor = _kg_per_ton / 0.8
feedstock_price = 71.3 / _feedstock_factor

# $/Mg
default_costs = {
    'Grower': 23.94,
    'Harvest': 20.72,
    'Storage': 7.18,
    'Transportation': 16.14,
    'Preprocessing': 24.35
    }

def set_feedstock_price(feedstock, preprocessing=None):
    '''Set price from $/Mg-dry to $/kg-wet for the feedstock stream.'''
    price = sum(i for i in default_costs.values())
    if preprocessing:
        price = price - default_costs['Preprocessing'] + preprocessing
    feedstock.price = price/1e3/(1-feedstock.imass['Water']/feedstock.F_mass)
    return feedstock.price

# 2.86 is the average motor gasoline price between 2010-2019 in 2016 $/gal
# based on AEO from EIA, density of gasoline is 2.819 kg/gal
# based on Lower and Higher Heating Values of Hydrogen and Other Fuels
# from H2 Tools maintained by Pacific Northwest National Laboratory
# (https://h2tools.org/hyarc/calculator-tools/lower-and-higher-heating-values-fuels)
denaturant_price = 2.86 / 2.819

# 1.41e6 is $/yr and 4279 in kg/hr from Table 33 of ref [2] (BDO scenario)
# 7880 is operating hours/yr on Page 10 of ref [2],
# cost is negative because it's a product stream
ash_disposal_price = -1.41e6 / (4279*7880)

# Baseline from ref [2], lower bound is 2015-2019 average of
# hydrate lime in $/ton at plant from Mineral Commodity Summaries 2020.
# 2015: 146.40 * (1.114/1.100) / 907.18474 = 0.163
# 2016: 145.50 / 907.18474 = 0.160
# 2017: 147.10 * (1.114/1.134) / 907.18474 = 0.159
# 2018: 151.50 * (1.114/1.157) / 907.18474 = 0.161
# 2019: 151.00 * (1.114/1.185) / 907.18474 = 0.156
# (0.163+0.160+0.159+0.161+0.156) / 5 = 0.160
# Upper bound is +10% from baseline = 0.1189 * _lb_per_kg * 1.1 = 0.288
lime_price = 0.1189 * _lb_per_kg

# The original cost is $466,183 every 5 years in ref [1], converted to per hour using
# the assumed 96% uptime
baghouse_bag_price = 466183/5/(24*365*0.96) * _GDP_2007to2016

# $5/MM BTU
CH4_LHV = chems.CH4.LHV
CH4_MW = chems.CH4.MW
CH4_cost_per_J = 5/(1e6*_J_per_BTU)
CH4_cost_per_mol = CH4_cost_per_J * -CH4_LHV
natural_gas_price = CH4_cost_per_mol * (1000/CH4_MW)


# All in 2016$/kg
price = {'Feedstock': feedstock_price,
         'H2SO4': 0.0430 * _lb_per_kg,
         # 0.1900 is for NH3
         'NH3': 0.1900 * _lb_per_kg,
         'NH4OH': 0.1900 * _lb_per_kg * 17.031/35.046,
         'NaOH': 0.2384 * _lb_per_kg,
         'CSL': 0.0339 * _lb_per_kg,
         'DAP': 0.1645 * _lb_per_kg,
         # $6.16/kg protein in 2016$, P25 of ref [2]
         'Enzyme': 6.16,
         'H2': 0.7306 * _lb_per_kg,
         'Hydrogenation catalyst': 528 * _lb_per_kg,
         'WWT polymer': 2.6282 * _lb_per_kg,
         'Natural gas': natural_gas_price,
         'Lime': lime_price,
         'Boiler chems': 2.9772 * _lb_per_kg,
         'Baghouse bag': baghouse_bag_price,
         'Cooling tower chems': 1.7842 * _lb_per_kg,
         'Makeup water': 0.0002 * _lb_per_kg,
         # Cost of ash is negative because it's a product stream
         'Ash disposal': ash_disposal_price,
         'Electricity': 0.068,
         'Denaturant': denaturant_price, # n-Heptane
         'Ethanol': 0.3370 * _lb_per_kg,
         'Adipic acid': 0.8554 * _lb_per_kg,
         'Sodium sulfate': 0.0706 * _lb_per_kg
         }

bst.PowerUtility.price = price['Electricity']

# =============================================================================
# Characterization factors (CFs) for life cycle analysis (LCA), 100-year global
# warming potential (GWP) in kg CO2-eq/kg, from ref [3] if not
# =============================================================================

GWP_CFs = {
    'H2SO4': 44.47/1e3,
    'NH3': 2.64,
    'NH4OH': 2.64 * chems.NH3.MW/chems.NH4OH.MW,
    'NaOH': 2.11,
    'CSL': 1.55,
    'DAP': 1.20,
    'Enzyme': 2.24,
    'H2': 15.80, # liquid H2 combined
    'CH4': 0.40, # NA NG from shale and conventional recovery
    'Lime': 1.29,
    'Denaturant': 0.88, # gasoline blendstock from crude oil for use in US refineries,
    'AdipicAcid': -12.03, # negative as it's a coproduct
    'SodiumSulfate': -0.47 # negative as it's a coproduct
    }

GWP_CF_array = chems.kwarray(GWP_CFs)
# In kg CO2-eq/kg of material
GWP_CF_stream = tmo.Stream('GWP_CF_stream', GWP_CF_array, units='kg/hr')

GWP_CFs['Corn stover'] = 44.70/1e3
GWP_CFs['Switchgrass'] = 87.81/1e3
GWP_CFs['Miscanthus'] = 78.28/1e3
# In kg CO2-eq/kWh
GWP_CFs['Electricity'] = 0.48

# [4] ecoinvent 3.6 https://www.ecoinvent.org/home.html (accessed Aug 26, 2020).
# # From ref [4], cut-off by classification, adipic acid production, RoW, TRACI
# GWP_CFs['AdipicAid_ecoinvent'] = 14.3
# # From ref [4], cut-off by classification, sodium sulfate production,
# # from natural sources, RoW, TRACI
# GWP_CFs['SodiumSulfate_ecoinvent'] = 0.10829

CFs = {'GWP_CFs': GWP_CFs, 'GWP_CF_stream': GWP_CF_stream}