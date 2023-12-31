#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Bioindustrial-Park: BioSTEAM's Premier Biorefinery Models and Results
# Copyright (C) 2020-, Yalin Li <mailto.yalin.li@gmail.com>,
#                      Sarang Bhagwat <sarangb2@illinois.edu>,
#                      Yoel Cortes-Pena <yoelcortes@gmail.com>
#
# This module is under the UIUC open-source license. See
# github.com/BioSTEAMDevelopmentGroup/biosteam/blob/master/LICENSE.txt
# for license details.

'''
References
----------
[1] Davis et al., Process Design and Economics for the Conversion of Lignocellulosic
    Biomass to Hydrocarbon Fuels and Coproducts: 2018 Biochemical Design Case Update;
    NREL/TP-5100-71949; National Renewable Energy Lab (NREL), 2018.
    https://doi.org/10.2172/1483234
[2] Aden et al., Process Design Report for Stover Feedstock: Lignocellulosic
    Biomass to Ethanol Process Design and Economics Utilizing Co-Current Dilute
    Acid Prehydrolysis and Enzymatic Hydrolysis for Corn Stover; NREL/TP-510-32438;
    National Renewable Energy Lab (NREL), 2002.
    https://doi.org/10.2172/1218326.
[3] Argonne National Laboratory. The Greenhouse gases, Regulated Emissions,
    and Energy use in Transportation (GREET) Model https://greet.es.anl.gov/
    (accessed Aug 25, 2020).
[4] Roni et al., Herbaceous Feedstock 2018 State of Technology Report;
    INL/EXT-18-51654-Rev000; Idaho National Lab. (INL), 2020.
    https://doi.org/10.2172/1615147.
[5] ecoinvent 3.6 https://www.ecoinvent.org/home.html (accessed Aug 26, 2020).

'''

import biosteam as bst

__all__ = ('load_process_settings', 'price', 'set_GWPCF', 'set_FECCF',)


# %%

# =============================================================================
# Prices for techno-economic analysis (TEA), all in $/kg (electricity in $/kWh)
# and from ref [1] if not noted
# =============================================================================

_kg_per_ton = 907.1847 # auom('ton').conversion_factor('kg')
_lb_per_kg = 2.2046 # auom('kg').conversion_factor('lb')
_liter_per_gallon = 3.7854 # auom('gal').conversion_factor('L')
_ft3_per_m3 = 35.3147 # auom('m3').conversion_factor('ft3')
_chemical_2020to2016 = 102.5 / 113.8 # average of Jan and Feb
_GDP_2007to2016 = 1.160

# From USD/dry-ton to USD/kg in 2016$, 20% moisture content,
# baseline and lower bound (60) from ref [1], upper bound (146.4) from
# Hartley et al., ACS Sustainable Chem. Eng. 2020, 8 (19), 7267–7277.
# https://doi.org/10.1021/acssuschemeng.9b06551.
_feedstock_factor = _kg_per_ton / 0.8
feedstock_price = 71.3 / _feedstock_factor

# Baseline from ref [1], lower and upper bounds (96% and 110% of baseline)
# calculated using the index of sulfuric acid from U.S. Bureau of Labor Statistics
# (Producer Price Index by Commodity for Chemicals and Allied Products)
# https://fred.stlouisfed.org/series/WPU0613020T1 (accessed Jul 31, 2020).
sulfuric_acid_price = 0.0430 * _lb_per_kg

# 2.2 is the average whole-sale ethanol price between 2010-2019 in 2016 $/gal
# based on Annual Energy Outlook (AEO) from Energy Information Administration (EIA)
# (https://www.eia.gov/outlooks/aeo/), which is $0.732/gal and similar to the
# 2.2/(2988/1e3) = $0.736/gal based on a density of 2988 g/gal from H2 Tools
# Lower and upper bounds are $1.37/gal and $2.79/gal, or $0.460/kg and $0.978/kg
_ethanol_V = 5.8617e-5 # chemicals.Ethanol.V('l', 298.15, 101325), molar volume in m3/mol
_ethanol_MW = 46.06844 # chemicals.Ethanol.MW
_ethanol_kg_2_gal = _liter_per_gallon/_ethanol_V*_ethanol_MW/1e6
ethanol_price = 2.2 / _ethanol_kg_2_gal

# Cost is negative because it's a product stream
ash_disposal_price = -1.41e6 / (4279*7880)

# Assume no cost/credit for baseline, the same as ash disposal for the lower bound,
# for the upper bound (i.e., positive selling price indicating profit), use
# USGS 2015-2019 average  free on bard price in $/metric tonne for crude gypsum.
# National Minerals Information Center. Mineral Commodity Summaries 2020;
# U.S. Geological Survey, 2020.
# Assuming all prices were in their nominal year (e.g., 2015 price in 2015$)
# and adjusted to 2016$
# 2015: 7.80 * 1.114 / 1.100 = 7.90
# 2016: 8.00
# 2017: 7.50 * 1.114 / 1.134 = 7.37
# 2018: 8.30 * 1.114 / 1.157 = 7.99
# 2019: 8.00 * 1.114 / 1.185 = 7.52
# (7.90+8.00+7.37+7.99+7.52) / 5 = 7.76 (in metric tonne)
# For the lower bound (i.e., negative selling price indicating cost), use price from
# ref [2]: $0.0094/lb in 2000$ = 0.0094*1.114/0.802*2.20462 = $0.0288/kg in 2016$
gypsum_price = 0

# Baseline from ref [1], lower bound is 2015-2019 average of
# hydrate lime in $/ton at plant from Mineral Commodity Summaries 2020.
# 2015: 146.40 * (1.114/1.100) / 907.18474 = 0.163
# 2016: 145.50 / 907.18474 = 0.160
# 2017: 147.10 * (1.114/1.134) / 907.18474 = 0.159
# 2018: 151.50 * (1.114/1.157) / 907.18474 = 0.161
# 2019: 151.00 * (1.114/1.185) / 907.18474 = 0.156
# (0.163+0.160+0.159+0.161+0.156) / 5 = 0.160
# Upper bound is +10% from baseline = 0.1189 * _lb_per_kg * 1.1 = 0.288
lime_price = 0.1189 * _lb_per_kg

baghouse_bag_price = 466183/5/(24*365*0.96) * _GDP_2007to2016

# 4.70 is the average natural gas price in 2016$/Mcf based on AEO from EIA,
# which is $0.231/kg at 273.15 K or $0.253/kg at 298.15 K using BioSTEAM,
# similar to the 4.7/1000/22*1000 = $0.214/kg at 273.15 K using 22 g/ft3 from H2 Tools
# Using the same conversion, lower and upper bounds (min/max of 2010-2019) should be
# $3.68/Mcf and $5.65/Mcf, or $0.198/kg and $0.304/kg
_CH4_V = 0.02442 # chemicals.CH4.V(298.15, 101325), molar volume in m3/mol
_CH4_MW = 16.04246 # chemicals.CH4.MW
natural_gas_price = 4.70/1e3*_ft3_per_m3*_CH4_V * (1e3/_CH4_MW)

# https://www.rightpricechemicals.com/buy-amberlyst-15-ion-exchange-resin.html
# USD 383.13 for 2.5kg (largest available size order), accessed 06/11/2020
amberlyst_15_price = 153.252 * _chemical_2020to2016

# All in 2016$/kg
price = {
    'Feedstock': feedstock_price,
    'H2SO4': 0.0430 * _lb_per_kg,
    # 0.1900 is for NH3
    'NH4OH': 0.1900 * _lb_per_kg * 0.4860, # chemicals.NH3.MW/chemicals.NH4OH.MW,
    'CSL': 0.0339 * _lb_per_kg,
    'Enzyme': 6.16,
    'Lime': lime_price,
    'Amberlyst15': amberlyst_15_price,
    'NaOH': 0.2384 * _lb_per_kg,
    'WWT polymer': 2.6282 * _lb_per_kg,
    'Boiler chems': 2.9772 * _lb_per_kg,
    'Cooling tower chems': 1.7842 * _lb_per_kg,
    'Makeup water': 0.0002 * _lb_per_kg,
    # Cost of ash is negative because it's a product stream
    'Ash disposal': ash_disposal_price,
    'Gypsum': gypsum_price,
    'Ethanol': ethanol_price,
    'Baghouse bag': baghouse_bag_price,
    'Natural gas': natural_gas_price,
    'Electricity': 0.070, # $/kWh, from EIA AEO, 2010-2019 average (0.067-0.074 range)
    'Lactic acid': 1.9, # the average of $1.7-2.1/kg
    }


# %%

# =============================================================================
# Characterization factors (CFs) for life cycle analysis (LCA), all from ref [3]
# if not noted, note that it is unclear if in-plant receiving and preprocessing
# (~50% of the total impact per ref [4]) of feedstock is included in ref [3]
# =============================================================================

##### 100-year global warming potential (GWP) in kg CO2-eq/kg unless noted otherwise #####
GWP_CFs = {
    'CH4': 0.40, # NA NG from shale and conventional recovery
    'CSL': 1.55,
    'Electricity': (0.48, 0.48), # assume production==consumption, both in kg CO2-eq/kWh
    'Enzyme': 2.24, # won't make a big diff (<4%) if it's 12.24 (~ ecoinvent value)
    'Ethanol': 1.44,
    'H2SO4': 44.47/1e3,   
    'Lime': 1.29 * 56.0774/74.093, # CaO to Ca(OH)2
    'NaOH': 2.11,
    'NH4OH': 2.64 * 0.4860, # chemicals.NH3.MW/chemicals.NH4OH.MW,    
    }

# Not used, just as a reference
ref_GWP_CFs = {}
ref_GWP_CFs['CaCO3'] = 10.30/1e3
ref_GWP_CFs['Gypsum'] = -4.20/1e3
# Lactic acid from corn stover
ref_GWP_CFs['Lactic acid_GREET'] = 1.80
# From ref [5], lactic acid production, RoW, TRACI global warming,
# substitution, consequential, long-term
ref_GWP_CFs['Lactic acid_fossil'] = 5.2796


##### Fossil energy consumption (FEC), in MJ/kg of material unless noted otherwise #####
FEC_CFs = {
    'CH4': 50, # NA NG from shale and conventional recovery
    'CSL': 12,
    'Electricity': (5.926, 5.926), # assume production==consumption, both in MJ/kWh
    'Ethanol': 16,
    'Enzyme': 26,
    'H2SO4': 568.98/1e3,
    'Lime': 4.896 * 56.0774/74.093, # CaO to Ca(OH)2
    'NaOH': 29,
    'NH4OH': 42 * 0.4860, # chemicals.NH3.MW/chemicals.NH4OH.MW,
    }

# Not used, just as a reference
ref_FEC_CFs = {}
ref_FEC_CFs['CaCO3'] = 133.19/1e3
ref_FEC_CFs['Gypsum'] = -44.19/1e3
# From corn stover
FEC_CFs['Lactic acid'] = 29
# From ref [5], lactic acid production, RoW, cumulative energy demand, fossil,
# substitution, consequential, long-term
FEC_CFs['Lactic acid_fossil'] = 91.265


def set_GWPCF(obj, name='', dilution=None):
    if not dilution: obj.characterization_factors['GWP'] = GWP_CFs[name]
    else: obj.characterization_factors['GWP'] = GWP_CFs[name] * dilution

def set_FECCF(obj, name='', dilution=None):
    if not dilution: obj.characterization_factors['FEC'] = FEC_CFs[name]
    else: obj.characterization_factors['FEC'] = FEC_CFs[name] * dilution
    
    
# %%

def load_process_settings(CE=541.7): # year 2016
    bst.CE = CE

    # These settings are sufficient to get baseline lactic acid price within $0.002/kg
    # of the final stabilized results
    bst.System.default_converge_method = 'fixed-point' # aitken isn't stable
    bst.System.default_maxiter = 1500
    bst.System.default_molar_tolerance = 0.02

    lps = bst.HeatUtility.get_heating_agent('low_pressure_steam')
    mps = bst.HeatUtility.get_heating_agent('medium_pressure_steam')
    hps = bst.HeatUtility.get_heating_agent('high_pressure_steam')
    mps.T = 233 + 273.15
    hps.T = 266 + 273.15

    cooling = bst.HeatUtility.get_cooling_agent('cooling_water')
    cooling.regeneration_price = 0
    cooling.T = 28 + 273.15
    cooling.T_limit = cooling.T + 9

    # Side steam in CHP not a heat utility, thus will cause problem in TEA utility
    # cost calculation if price not set to 0 here, costs for regeneration of heating
    # and cooling utilities will be considered as CAPEX and OPEX of CHP and CT, respectively
    for i in (lps, mps, hps, cooling):
        i.heat_transfer_price = i.regeneration_price = 0

    bst.PowerUtility.price = price['Electricity']
    set_GWPCF(bst.PowerUtility, 'Electricity')
    set_FECCF(bst.PowerUtility, 'Electricity')