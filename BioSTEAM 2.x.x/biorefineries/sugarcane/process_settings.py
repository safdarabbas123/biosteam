# -*- coding: utf-8 -*-
"""
Created on Mon Feb  4 10:02:05 2019

@author: yoelr
"""
import biosteam as bst

__all__ = ('price',)

# %% Process settings

def set_lipidcane_process_settings():
    bst.CE = 567 # 2013
    bst.PowerUtility.price = 0.065
    HeatUtility = bst.HeatUtility
    steam_utility = HeatUtility.heating_agents['Low pressure steam']
    steam_utility.efficiency = 0.85
    steam_utility.T = 529.2
    steam_utility.P = 44e5
    steam_utility.price_kmol = 0.30626
    steam_utility.Hvap = 30235.86
    HeatUtility.cooling_agents['Cooling water'].price_kmol = 0
    HeatUtility.cooling_agents['Chilled water'].price_kJ = 0
    bst.find.set_flowsheet('lipidcane')

# Raw material price (USD/kg)
price = {'Sugar cane': 0.03455, # 70% m.c
         'Water': 0.000353,
         'HCl': 0.205,
         'Lime': 0.077,
         'H3PO4': 0,#0.700, # TODO: find price
         'NaOH':0.41,
         'Protease': 0.5,
         'Polymer': 0, # TODO: find price
         'Steam': 0.017,
         'Ethanol': 0.789,
         'Waste': -0.33,
         'Gasoline': 0.756} # 2 USD/gal

set_lipidcane_process_settings()
