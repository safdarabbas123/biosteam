# -*- coding: utf-8 -*-
# BioSTEAM: The Biorefinery Simulation and Techno-Economic Analysis Modules
# Copyright (C) 2020, Yoel Cortes-Pena <yoelcortes@gmail.com>
# 
# This module is under the UIUC open-source license. See 
# github.com/BioSTEAMDevelopmentGroup/biosteam/blob/master/LICENSE.txt
# for license details.
"""
The complete oilcane biorefinery system is created here.

"""
import flexsolve as flx
import thermosteam as tmo
import biosteam as bst
from biosteam import main_flowsheet as f
from biosteam import SystemFactory
from ..sugarcane import (
    create_bagasse_pelleting_system,
    create_sucrose_fermentation_system,
    create_sucrose_to_ethanol_system,
    create_beer_distillation_system,
    create_ethanol_purification_system_after_beer_column,
)
from ..lipidcane import (
    create_feedstock_handling_system,
    create_juicing_system,
    create_lipid_pretreatment_system as create_oil_pretreatment_system,
    create_juicing_and_lipid_extraction_system as create_juicing_and_oil_extraction_system,
    create_transesterification_and_biodiesel_separation_system,
    create_lipidcane_to_biodiesel_and_conventional_ethanol_system as create_oilcane_to_biodiesel_and_conventional_ethanol_system,
    price,
)
import biorefineries as brf
from biorefineries.oilcane import units
from collections import deque

__all__ = (
    'create_oilcane_to_biodiesel_and_ethanol_1g',
    'create_oilcane_to_biodiesel_and_ethanol_combined_1_and_2g_post_fermentation_oil_separation',
    'create_oilcane_to_crude_oil_and_ethanol_1g',
    'create_oilcane_to_crude_oil_and_ethanol_combined_1_and_2g_post_fermentation_oil_separation',
    'create_sugarcane_to_ethanol_combined_1_and_2g',
    'create_oilcane_to_biodiesel_1g',
    'create_oilcane_to_biodiesel_combined_1_and_2g_post_fermentation_oil_separation',
)

oilcane_dct = create_juicing_and_oil_extraction_system.ins[0].copy()
oilcane_dct['ID'] = 'oilcane'
TAG = oilcane_dct['TAG']
oilcane_dct['TAG'] = 0.80 * TAG
oilcane_dct['PL'] = 0.10 * TAG
oilcane_dct['FFA'] = 0.10 * TAG

@SystemFactory(
    ID='oil_expression_sys',
    ins=[dict(ID='bagasse_pellets')],
    outs=[dict(ID='oil'),
          dict(ID='pressed_bagasse')], 
)
def create_oil_expression_system(ins, outs):
    bagasse_pellets, = ins
    oil, pressed_bagasse = outs
    U801 = bst.ScrewPress('U801', bagasse_pellets, (oil, pressed_bagasse),
                          split={'Lipid': 0.55}, moisture_content=0.14)
    U801.cost_items = U801.cost_items.copy() 
    U801.cost_items['Screw press'] = cost_item = U801.cost_items['Screw press'].copy()
    cost_item.ub = 24000
    U801.tag = "bagasse oil extraction"

@SystemFactory(
    ID='post_fermentation_oil_separation_sys',
    ins=[dict(ID='solids_free_stillage')],
    outs=[dict(ID='oil'),
          dict(ID='wastewater'),
          dict(ID='evaporator_condensate')], 
)
def create_post_fermentation_oil_separation_system(ins, outs, wastewater_concentration=None,
                                                   target_oil_content=60, pop_last_evaporator=True,
                                                   separate_cellmass=False):
    oil, wastewater, evaporator_condensate = outs
    if separate_cellmass:     
        cellmass = bst.Stream('cellmass')
        outs.insert(1, cellmass)
    V605 = bst.MixTank('V605', ins)
    P606 = bst.Pump('P606', V605-0)
    Ev607 = bst.MultiEffectEvaporator('Ev607',
        ins=P606-0,
        P=(101325, 69682, 47057, 30953),
        V=0.90, V_definition='First-effect',
        thermo=oil.thermo.ideal(),
    )
    Ev607.target_oil_content = target_oil_content # kg / kg
    Ev607.pop_last_evaporator = pop_last_evaporator
    Ev607.remove_evaporators = False
    P_original = tuple(Ev607.P)
    @Ev607.add_specification(run=False)
    def adjust_evaporation():
        EvX = Ev607
        V_last = EvX.V
        def x_oil(V):
            EvX.V = V
            EvX._run()
            effluent = EvX.outs[0]
            oil = effluent.imass['Oil']
            total = effluent.imass['Oil', 'Water'].sum()
            return EvX.target_oil_content - 1000 * oil / total
        
        x0 = 0.
        x1 = 0.5
        y0 = x_oil(x0)
        EvX.P = P_original
        EvX._reload_components = True
        if y0 <= 0.:
            EvX.V = x0
            return
        elif EvX.remove_evaporators:
            pop_last_evaporator = EvX.pop_last_evaporator
            if pop_last_evaporator:
                EvX.P = list(P_original)
            else:
                EvX.P = deque(P_original)
            EvX._load_components()
            for i in range(EvX._N_evap-1):
                if x_oil(1e-6) < 0.:
                    if pop_last_evaporator:
                        EvX.P.pop()
                    else:
                        EvX.P.popleft()
                    EvX._reload_components = True
                else:
                    break    
            y1 = x_oil(x1)
            EvX.V = flx.IQ_interpolation(x_oil, x0, x1, y0, y1, x=V_last, ytol=1e-5, xtol=1e-6)
        elif x_oil(1e-6) < 0.:
            EvX.V = 1e-6
        else:
            y1 = x_oil(x1)
            EvX.V = flx.IQ_interpolation(x_oil, 1e-6, x1, y0, y1, x=V_last, ytol=1e-5, xtol=1e-6)
        
    P607 = bst.Pump('P607', Ev607-0, P=101325.)
    C603_2 = bst.LiquidsSplitCentrifuge('C603_2', P607-0, (oil, ''), 
                                        split={'Oil': 0.99,
                                               'Water': 0.0001})
    if separate_cellmass:        
        C603_3 = bst.SolidsCentrifuge('C603_3', C603_2-1, (cellmass, ''), 
                                      split={'Cellmass': 0.99}, solids=('Cellmass',))
        stream = C603_3-1
    else:
        stream = C603_2-1
    S601 = bst.Splitter('S601', ins=Ev607-1, outs=['', evaporator_condensate], split=0.5)
    M601 = bst.Mixer('M601', [S601-0, stream], wastewater)
    M601.target_wastewater_concentration = 60. # kg / m3
    @M601.add_specification(run=True)
    def adjust_wastewater_concentration():
        concentrated_wastewater = C603_2.outs[1]
        waste = concentrated_wastewater.F_mass - concentrated_wastewater.imass['Water'] 
        current_concentration = waste / concentrated_wastewater.F_vol
        required_water = (1./M601.target_wastewater_concentration - 1./current_concentration) * waste * 1000.
        F_mass = S601.ins[0].F_mass
        if F_mass:
            split = required_water / F_mass
            if split < 0:
                split = 0.
            elif split > 1.:
                split = 1.
            S601.split[:] = split
            for i in S601.path_until(M601): i._run()

@SystemFactory(
    ID='oilcane_sys',
    ins=[oilcane_dct],
    outs=[*create_oilcane_to_biodiesel_and_conventional_ethanol_system.outs[:3],
          dict(ID='vinasse')], 
)
def create_oilcane_to_biodiesel_and_ethanol_1g(
        ins, outs,
        evaporator_and_beer_column_heat_integration=True,
    ):
    oilcane, = ins
    ethanol, biodiesel, crude_glycerol, vinasse = outs
    
    feedstock_handling_sys = create_feedstock_handling_system(
        ins=oilcane,
        outs='',
        mockup=True,
        area=100
    )
    
    ### Oil and juice separation ###
    
    juicing_sys, jdct = create_juicing_system(
        ins=feedstock_handling_sys-0,
        outs=['', 'bagasse', 'fiber_fines'],
        pellet_bagasse=False,
        mockup=True,
        udct=True,
        area=200,
    )
    screened_juice, bagasse, fiber_fines = juicing_sys.outs
    # bagasse_pelleting_sys = create_bagasse_pelleting_system(None, bagasse, area=200, mockup=True)
    # pelleted_bagasse, = bagasse_pelleting_sys.outs
    jdct['S201'].isplit['Lipid'] = 1.
    crushing_mill = jdct['U201']
    crushing_mill.tag = "oil extraction"
    crushing_mill.isplit['Lipid'] = 0.90
    
    ### Ethanol section ###
    
    ethanol_production_sys, epdct = create_sucrose_to_ethanol_system(
        ins=[screened_juice, 'denaturant'],
        outs=[ethanol, '', '', ''],
        mockup=True,
        area=300,
        udct=True,
    )
    ethanol, stillage, stripper_bottoms_product, evaporator_condensate_a = ethanol_production_sys.outs
    post_fermentation_oil_separation_sys = create_post_fermentation_oil_separation_system(
        ins=stillage,
        outs=['', '', ''],
        mockup=True,
        area=400,
    )
    oil, thick_vinasse, evaporator_condensate_b = post_fermentation_oil_separation_sys.outs
    oil_pretreatment_sys, oil_pretreatment_dct = create_oil_pretreatment_system(
        ins=oil,
        mockup=True,
        outs=['', 'polar_lipids', ''],
        area=600,
        udct=True,
    )
    MX = bst.Mixer(400, [thick_vinasse, evaporator_condensate_a], vinasse)
    oil, polar_lipids, wastewater = oil_pretreatment_sys.outs
    
    
    ### Biodiesel section ###
    
    # Fresh degummed oil
    transesterification_and_biodiesel_separation_sys, tbdct = create_transesterification_and_biodiesel_separation_system(
        ins=oil, 
        outs=[biodiesel, crude_glycerol, ''],
        mockup=True,
        area=600,
        udct=True,
    )
    MX = bst.Mixer(600, [transesterification_and_biodiesel_separation_sys-2, wastewater], 'wastewater')

    ### Facilities ###
    s = f.stream
    u = f.unit
    MX2 = bst.Mixer(700,
        [polar_lipids, bagasse]
    )
    # Burn bagasse from conveyor belt
    bst.BoilerTurbogenerator(700,
        (MX2-0, '', 
         'boiler_makeup_water',
         'natural_gas',
         'FGD_lime',
         'boilerchems'),
        ('emissions', 'rejected_water_and_blowdown', 'ash_disposal'),
        boiler_efficiency=0.80,
        turbogenerator_efficiency=0.85
    )
    bst.CoolingTower(800)
    makeup_water_streams = (s.cooling_tower_makeup_water,
                            s.boiler_makeup_water)
    process_water_streams = (s.imbibition_water,
                             s.biodiesel_wash_water,
                             s.oil_wash_water,
                             s.rvf_wash_water,
                             s.stripping_water,
                             *makeup_water_streams)
    makeup_water = bst.Stream('makeup_water', price=0.000254)
    MX = bst.Mixer(800, [evaporator_condensate_b, stripper_bottoms_product], 'recycle_process_water')
    bst.ChilledWaterPackage(800)
    bst.ProcessWaterCenter(800,
        (MX-0, makeup_water),
        (),
        None,
        makeup_water_streams,
        process_water_streams
    )
    HXN = bst.HeatExchangerNetwork(900, 
        ignored=lambda: [u.E301, u.D601.boiler, u.D602.boiler, u.H601, u.H602, u.H603, u.H604, oil_pretreatment_dct['F3']],
        Qmin=1e5,
    )
    HXN.acceptable_energy_balance_error = 0.01

@SystemFactory(
    ID='oilcane_sys',
    ins=[oilcane_dct],
    outs=[dict(ID='ethanol', price=price['Ethanol']),
          dict(ID='crude_oil', price=price['Crude oil']),
          dict(ID='vinasse')], 
)
def create_oilcane_to_crude_oil_and_ethanol_1g(
        ins, outs,
        evaporator_and_beer_column_heat_integration=True,
    ):
    oilcane, = ins
    ethanol, crude_oil, vinasse = outs
    
    feedstock_handling_sys = create_feedstock_handling_system(
        ins=oilcane,
        outs='',
        mockup=True,
        area=100
    )
    
    ### Oil and juice separation ###
    
    juicing_sys, jdct = create_juicing_system(
        ins=feedstock_handling_sys-0,
        outs=['', '', 'fiber_fines'],
        pellet_bagasse=False,
        mockup=True,
        udct=True,
        area=200,
    )
    screened_juice, bagasse, fiber_fines = juicing_sys.outs
    # bagasse_pelleting_sys = create_bagasse_pelleting_system(None, bagasse, area=200, mockup=True)
    # pelleted_bagasse, = bagasse_pelleting_sys.outs
    jdct['S201'].isplit['Lipid'] = 1. # Vibrating screen
    crushing_mill = jdct['U201']
    crushing_mill.tag = "oil extraction"
    crushing_mill.isplit['Lipid'] = 0.90
    
    ### Ethanol section ###
    
    ethanol_production_sys, epdct = create_sucrose_to_ethanol_system(
        ins=[screened_juice, 'denaturant'],
        outs=[ethanol, '', '', ''],
        mockup=True,
        area=300,
        udct=True,
    )
    ethanol, stillage, stripper_bottoms_product, evaporator_condensate_a = ethanol_production_sys.outs
    post_fermentation_oil_separation_sys = create_post_fermentation_oil_separation_system(
        ins=stillage,
        outs=[crude_oil, '', ''],
        mockup=True,
        area=400,
    )
    crude_oil, thick_vinasse, evaporator_condensate_b = post_fermentation_oil_separation_sys.outs
    MX = bst.Mixer(400, [thick_vinasse, evaporator_condensate_a], vinasse)
    
    ### Facilities ###
    
    s = f.stream
    u = f.unit
    
    # Burn bagasse from conveyor belt
    bst.BoilerTurbogenerator(700,
        (bagasse, '', 
         'boiler_makeup_water',
         'natural_gas',
         'FGD_lime',
         'boilerchems'),
        ('emissions', 'rejected_water_and_blowdown', 'ash_disposal'),
        boiler_efficiency=0.80,
        turbogenerator_efficiency=0.85
    )
    bst.CoolingTower(800)
    makeup_water_streams = (s.cooling_tower_makeup_water,
                            s.boiler_makeup_water)
    process_water_streams = (s.imbibition_water,
                             s.oil_wash_water,
                             s.rvf_wash_water,
                             s.stripping_water,
                             *makeup_water_streams)
    makeup_water = bst.Stream('makeup_water', price=0.000254)
    MX = bst.Mixer(800, [evaporator_condensate_b, stripper_bottoms_product], 'recycle_process_water')
    bst.ChilledWaterPackage(800)
    bst.ProcessWaterCenter(800,
        (MX-0, makeup_water),
         (),
         None,
         makeup_water_streams,
         process_water_streams
    )
    HXN = bst.HeatExchangerNetwork(900, 
        ignored=lambda: [u.E301],
        Qmin=1e5,
    )
    HXN.acceptable_energy_balance_error = 0.01

@SystemFactory(
    ID='cane_to_fermentation_sys',
    ins=[dict(ID='cane')],
    outs=[dict(ID='beer'),
          dict(ID='lignin'),
          dict(ID='condensate'),
          dict(ID='pretreatment_wastewater'),
          dict(ID='fiber_fines')],
)
def create_cane_to_combined_1_and_2g_fermentation(
        ins, outs, titer=None, productivity=None, product_group=None,
        SeedTrain=None, CoFermentation=None, ignored_volume=None,
        cofermentation_reactions=None,
        seed_train_reactions=None,
    ):
    """
    Create a system that produces crude oil and a fermentation-derived product 
    (without purification).
    
    """
    oilcane, = ins
    beer, lignin, condensate, pretreatment_wastewater, fiber_fines = outs
    if SeedTrain is None: SeedTrain = units.SeedTrain
    if CoFermentation is None: CoFermentation = units.CoFermentation
    if product_group is None: product_group = 'Ethanol'
    if productivity is None: productivity = 0.95
    if titer is None: titer = 68.5
    
    feedstock_handling_sys = create_feedstock_handling_system(
        ins=oilcane,
        outs='',
        mockup=True,
        area=100
    )
    juicing_sys, udct = create_juicing_system(
        ins=feedstock_handling_sys-0,
        outs=['', 'bagasse', fiber_fines],
        mockup=True,
        udct=True,
        area=200,
        pellet_bagasse=False,
    )
    screened_juice, bagasse, fiber_fines = juicing_sys.outs
    
    udct['S201'].isplit['Lipid'] = 1. # Vibrating screen
    crushing_mill = udct['U201']
    crushing_mill.tag = "oil extraction"
    crushing_mill.isplit['Lipid'] = 0.90
    conveying_belt = bagasse.source
    conveying_belt.cellulose_rxn = tmo.Reaction('Cellulose -> Glucan', 'Cellulose', 1.0, basis='wt')
    conveying_belt.cellulose_rxn.basis = 'mol'
    # Bagasse composition https://www.sciencedirect.com/science/article/pii/S0144861710005072
    # South american; by HPLC
    # Glucan: 41.3%
    # Xylan: 24.9%
    # Galactan: 0.6%
    # Arabinan: 1.7%
    # Lignin: 23.2%
    # Acetyl: 3.0%
    conveying_belt.hemicellulose_rxn = tmo.Reaction('30.2 Hemicellulose -> 24.9 Xylan + 1.7 Arabinan + 0.6 Galactan + 3 Acetate', 'Hemicellulose', 1.0, basis='wt')
    conveying_belt.hemicellulose_rxn.basis = 'mol'
    def convert_hemicellulose():
        conveying_belt._run()
        bagasse = conveying_belt.outs[0]
        conveying_belt.cellulose_rxn(bagasse)
        conveying_belt.hemicellulose_rxn(bagasse)
        
    conveying_belt.specification = convert_hemicellulose
    hot_water_pretreatment_sys, hw_dct = brf.cornstover.create_hot_water_pretreatment_system(
        outs=('', pretreatment_wastewater),
        ins=bagasse,
        mockup=True,
        area=300,
        udct=True,
        solids_loading=0.50, # 50 wt/wt % solids content
    )
    hydrolyzate, pretreatment_wastewater = hot_water_pretreatment_sys.outs
    
    cellulosic_fermentation_sys, cf_dct = brf.cornstover.create_cellulosic_fermentation_system(
        ins=(hydrolyzate,),
        outs=['vent', beer, lignin],
        mockup=True,
        area=400,
        udct=True,
        kind='Saccharification and Co-Fermentation',
        cofermentation_reactions=cofermentation_reactions,
        seed_train_reactions=seed_train_reactions,
        insoluble_solids_loading=0.23,
        SeedTrain=SeedTrain,
        CoFermentation=CoFermentation,
        add_nutrients=False,
        solids_loading=0.23, # 30 wt/vol % solids content in saccharification
    )
    # DAP_storage = cf_dct['DAP_storage']
    # CSL_storage = cf_dct['CSL_storage']
    cofermentation = cf_dct['R303'] # Cofermentation
    pressurefilter = cf_dct['S303'] # Pressure filter
    pressurefilter.tag = "bagasse oil extraction"
    pressurefilter.isplit['Lipid'] = 1. - 0.7
    hydrolysate = pressurefilter.outs[1]
    sink = hydrolysate.sink
    sink.ins[0] = None
    MX = bst.Mixer(400, [hydrolysate, screened_juice])
    EvX = bst.MultiEffectEvaporator(400, ins=MX-0, outs=('', condensate),
                                    P=(101325, 69682, 47057, 30953, 19781),
                                    V_definition='First-effect',
                                    thermo=hydrolysate.thermo.ideal(),
                                    V=0.05) # fraction evaporated
    PX = bst.Pump(400, ins=EvX-0, P=101325.)
    MX = bst.Mixer(400, [PX-0, 'dilution_water'])
    HX = bst.HXutility(400, MX-0, T=305.15)
    HX-0-sink
    PX.sucrose_hydrolysis_reaction = tmo.Reaction(
        'Sucrose + Water -> 2Glucose', 'Sucrose', 1.00
    )

    @PX.add_specification(run=True)
    def hydrolysis():
        feed = PX.ins[0]
        PX.sucrose_hydrolysis_reaction.force_reaction(feed)
        if feed.imol['Water'] < 0: feed.imol['Water'] = 0.
    
    cofermentation.titer = titer
    cofermentation.productivity = productivity
    P_original = tuple(EvX.P)
    @EvX.add_specification(run=True)
    def evaporation():
        path = EvX.path_until(cofermentation, inclusive=True)
        beer = cofermentation.outs[1]
        target_titer = cofermentation.titer
        V_last = EvX.V
        EvX.P = P_original
        EvX._reload_components = True
        def f(V):
            EvX.V = V
            for unit in path: unit.run()
            ignored = beer.ivol[ignored_volume] if ignored_volume in cofermentation.chemicals else 0.
            ignored_product = sum([i.imass[product_group] for i in cofermentation.ins])
            return target_titer - (beer.imass[product_group] - ignored_product) / (beer.F_vol - ignored)
        MX.ins[1].imass['Water'] = 0.
        y0 = f(0)
        if y0 < 0.:
            ethanol = float(beer.imass[product_group])
            current_titer = ethanol / beer.F_vol
            required_water = (1./target_titer - 1./current_titer) * ethanol * 1000.
            MX.ins[1].imass['Water'] = max(required_water, 0)
        else:
            EvX.P = list(P_original)
            EvX._load_components()
            for i in range(EvX._N_evap-1):
                if f(1e-6) < 0.:
                    EvX.P.pop()
                    EvX._reload_components = True
                else:
                    break  
            x0 = 0.
            x1 = 0.1
            y1 = f(x1)
            while y1 > 0:
                if x1 > 0.9: raise RuntimeError('infeasible to evaporate any more water')
                x0 = x1            
                x1 += 0.1
                y1 = f(x1)
            EvX.V = flx.IQ_interpolation(f, x0, x1, y0, y1, x=V_last, ytol=1e-5, xtol=1e-6)
        cofermentation.tau = target_titer / cofermentation.productivity 

@SystemFactory(
    ID='oilcane_sys',
    ins=create_oilcane_to_biodiesel_and_ethanol_1g.ins,
    outs=[dict(ID='ethanol', price=price['Ethanol']),
          dict(ID='crude_oil', price=price['Crude oil'])],
)
def create_oilcane_to_crude_oil_and_ethanol_combined_1_and_2g_post_fermentation_oil_separation(ins, outs):
    oilcane, = ins
    ethanol, crude_oil = outs
    
    cane_to_fermentation_sys = create_cane_to_combined_1_and_2g_fermentation('cane_to_fermentation_sys', ins=oilcane)
    beer, lignin, condensate, pretreatment_wastewater, fiber_fines = cane_to_fermentation_sys.outs
    cellulosic_beer_distillation_sys = create_beer_distillation_system(
        ins=beer,
        outs=[''],
        mockup=True,
        area=400,
    )
    stripper_process_water = bst.Stream('')
    distilled_beer, stillage = cellulosic_beer_distillation_sys.outs
    ethanol_purification_sys, ep_dct = create_ethanol_purification_system_after_beer_column(
        ins=distilled_beer,
        outs=[ethanol, stripper_process_water],
        mockup=True,
        udct=True,
        area=400,
    )
    post_fermentation_oil_separation_sys, pfls_dct = create_post_fermentation_oil_separation_system(
        ins=stillage, outs=[crude_oil],
        mockup=True,
        area=600,
        udct=True,
        separate_cellmass=True,
    )
    backend_oil, cellmass, wastewater, evaporator_condensate = post_fermentation_oil_separation_sys.outs
    MX_process_water = bst.Mixer(800, (condensate, evaporator_condensate, stripper_process_water),
                                 'recycle_process_water')
    
    wastewater_treatment_sys = bst.create_wastewater_treatment_system(
        ins=[wastewater,
             fiber_fines,
             pretreatment_wastewater,
             evaporator_condensate],
        mockup=True,
        area=500,
    )
    s = f.stream
    M501 = bst.Mixer(700, (wastewater_treatment_sys-1, lignin, cellmass, f.stream.filter_cake))
    brf.cornstover.create_facilities(
        solids_to_boiler=M501-0,
        gas_to_boiler=wastewater_treatment_sys-0,
        process_water_streams=(s.imbibition_water,
                               s.oil_wash_water,
                               s.rvf_wash_water,
                               s.stripping_water,
                               s.caustic, 
                               s.warm_process_water,
                               s.pretreatment_steam,
                               s.saccharification_water),
        feedstock=s.bagasse,
        RO_water=wastewater_treatment_sys-2,
        recycle_process_water=MX_process_water-0,
        BT_area=700,
        area=800,
    )
    HXN = bst.HeatExchangerNetwork(900,
        Qmin=1e3,
    )
    HXN.acceptable_energy_balance_error = 0.01

@SystemFactory(
    ID='oilcane_sys',
    ins=create_oilcane_to_biodiesel_and_ethanol_1g.ins,
    outs=create_oilcane_to_biodiesel_and_ethanol_1g.outs[:-1],
)
def create_oilcane_to_biodiesel_and_ethanol_combined_1_and_2g_post_fermentation_oil_separation(ins, outs):
    oilcane, = ins
    ethanol, biodiesel, crude_glycerol = outs
    oilcane_to_fermentation_sys = create_cane_to_combined_1_and_2g_fermentation('oilcane_to_fermentation_sys', ins=oilcane)
    beer, lignin, condensate, pretreatment_wastewater, fiber_fines = oilcane_to_fermentation_sys.outs
    cellulosic_beer_distillation_sys = create_beer_distillation_system(
        ins=beer,
        outs=[''],
        mockup=True,
        area=400,
    )
    stripper_process_water = bst.Stream('')
    distilled_beer, stillage = cellulosic_beer_distillation_sys.outs
    ethanol_purification_sys, ep_dct = create_ethanol_purification_system_after_beer_column(
        ins=distilled_beer,
        outs=[ethanol, stripper_process_water],
        mockup=True,
        udct=True,
        area=400,
    )
    ethanol_purification_sys.outs
    post_fermentation_oil_separation_sys, pfls_dct = create_post_fermentation_oil_separation_system(
        ins=stillage,
        mockup=True,
        area=600,
        udct=True,
        separate_cellmass=True,
    )
    backend_oil, cellmass, wastewater, evaporator_condensate = post_fermentation_oil_separation_sys.outs
    backend_oil.ID = 'backend_oil'
    MX_process_water = bst.Mixer(900, (condensate, evaporator_condensate, stripper_process_water),
                                 'recycle_process_water')
    oil_pretreatment_sys, oil_pretreatment_dct = create_oil_pretreatment_system(
        ins=backend_oil,
        outs=['', 'polar_lipids', ''],
        mockup=True,
        area=800,
        udct=True
    )
    oil, polar_lipids, wastewater_small = oil_pretreatment_sys.outs
    
    transesterification_and_biodiesel_separation_sys = create_transesterification_and_biodiesel_separation_system(
        ins=oil, 
        outs=[biodiesel, crude_glycerol, ''],
        mockup=True,
        area=800,
    )
    wastewater_treatment_sys = bst.create_wastewater_treatment_system(
        ins=[wastewater,
             fiber_fines,
             pretreatment_wastewater,
             wastewater_small,
             transesterification_and_biodiesel_separation_sys-2,
             evaporator_condensate],
        mockup=True,
        area=500,
    )
    s = f.stream
    u = f.unit
    M501 = bst.Mixer(700, (wastewater_treatment_sys-1, lignin, polar_lipids, cellmass, f.stream.filter_cake))
    brf.cornstover.create_facilities(
        solids_to_boiler=M501-0,
        gas_to_boiler=wastewater_treatment_sys-0,
        process_water_streams=(s.imbibition_water,
                               s.biodiesel_wash_water,
                               s.oil_wash_water,
                               s.rvf_wash_water,
                               s.stripping_water,
                               s.caustic, 
                               s.warm_process_water,
                               s.pretreatment_steam,
                               s.saccharification_water),
        feedstock=s.bagasse,
        RO_water=wastewater_treatment_sys-2,
        recycle_process_water=MX_process_water-0,
        BT_area=700,
        area=900,
    )
    HXN = bst.HeatExchangerNetwork(1000,
        ignored=lambda: [u.D801.boiler, u.D802.boiler, u.H803, u.H802, u.H801, u.H804, u.H806, u.H809, oil_pretreatment_dct['F3']],
        Qmin=1e3,
    )
    HXN.acceptable_energy_balance_error = 0.01

@SystemFactory(
    ID='sugarcane_sys',
    ins=brf.sugarcane.create_sugarcane_to_ethanol_system.ins[:1],
    outs=brf.sugarcane.create_sugarcane_to_ethanol_system.outs[:1],
)
def create_sugarcane_to_ethanol_combined_1_and_2g(ins, outs):
    sugarcane, = ins
    ethanol, = outs
    cane_to_fermentation_sys = create_cane_to_combined_1_and_2g_fermentation('cane_to_fermentation_sys', ins=sugarcane)
    beer, lignin, condensate, pretreatment_wastewater, fiber_fines = cane_to_fermentation_sys.outs
    cellulosic_beer_distillation_sys = create_beer_distillation_system(
        ins=beer,
        outs=[''],
        mockup=True,
        area=400,
    )
    stripper_process_water = bst.Stream('')
    distilled_beer, stillage = cellulosic_beer_distillation_sys.outs
    ethanol_purification_sys, ep_dct = create_ethanol_purification_system_after_beer_column(
        ins=distilled_beer,
        outs=[ethanol, stripper_process_water],
        mockup=True,
        udct=True,
        area=400,
    )
    C603_3 = bst.SolidsCentrifuge(400, stillage, 
                                  split={'Cellmass': 0.99}, solids=('Cellmass',))
    wastewater_treatment_sys = bst.create_wastewater_treatment_system(
        ins=[C603_3-1,
             fiber_fines,
             pretreatment_wastewater],
        mockup=True,
        area=500,
    )
    s = f.stream
    M501 = bst.Mixer(700, (wastewater_treatment_sys-1, lignin, C603_3-0, s.filter_cake))
    MX = bst.Mixer(400, [condensate, stripper_process_water])
    brf.cornstover.create_facilities(
        solids_to_boiler=M501-0,
        gas_to_boiler=wastewater_treatment_sys-0,
        process_water_streams=(s.imbibition_water,
                               s.rvf_wash_water,
                               s.stripping_water,
                               s.caustic, 
                               s.warm_process_water,
                               s.pretreatment_steam,
                               s.saccharification_water),
        feedstock=s.bagasse,
        RO_water=wastewater_treatment_sys-2,
        recycle_process_water=MX-0,
        BT_area=700,
        area=900,
    )
    HXN = bst.HeatExchangerNetwork(1000,
        Qmin=1e3,
    )
    HXN.acceptable_energy_balance_error = 0.01
    # HXN.raise_energy_balance_error = True

@SystemFactory(
    ID='oilcane_sys',
    ins=[oilcane_dct],
    outs=[dict(ID='biodiesel', price=price['Biodiesel']),
          dict(ID='crude_glycerol', price=price['Crude glycerol']),
          'vinasse'],
)
def create_oilcane_to_biodiesel_1g(
            ins, outs,
        ):
    oilcane, = ins
    biodiesel, crude_glycerol, vinasse = outs
    
    feedstock_handling_sys = create_feedstock_handling_system(
        ins=oilcane,
        outs='',
        mockup=True,
        area=100
    )
    
    ### Oil and juice separation ###
    
    juicing_sys, jdct = create_juicing_system(
        ins=feedstock_handling_sys-0,
        outs=['', '', 'fiber_fines'],
        pellet_bagasse=False,
        mockup=True,
        udct=True,
        area=200,
    )
    screened_juice, bagasse, fiber_fines = juicing_sys.outs
    # bagasse_pelleting_sys = create_bagasse_pelleting_system(None, bagasse, area=200, mockup=True)
    # pelleted_bagasse, = bagasse_pelleting_sys.outs
    jdct['S201'].isplit['Lipid'] = 1. # Vibrating screen
    crushing_mill = jdct['U201']
    crushing_mill.tag = "oil extraction"
    crushing_mill.isplit['Lipid'] = 0.90
    
    ### Ethanol section ###
    fermrxn = tmo.Rxn('CO2 + Glucose -> H2O + TAG', 'Glucose', 0.9500, correct_atomic_balance=True)
    fermentation_sys, epdct = create_sucrose_fermentation_system(
        ins=[screened_juice],
        fermentation_reaction=fermrxn,
        titer=89.4,
        productivity=0.61,
        product_group='Lipid',
        mockup=True,
        area=300,
        udct=True,
    )
    fermentor = epdct['R301']
    fermentor.N = None
    fermentor.V = 3785.4118
    fermentor.Nmin = 2
    fermentor.Nmax = 36 
    product, condensate, vent = fermentation_sys.outs
    post_fermentation_oil_separation_sys = create_post_fermentation_oil_separation_system(
        ins=product,
        mockup=True,
        area=400,
    )
    oil, thick_vinasse, evaporator_condensate_b = post_fermentation_oil_separation_sys.outs
    oil_pretreatment_sys, oil_pretreatment_dct = create_oil_pretreatment_system(
        ins=oil,
        mockup=True,
        outs=['', 'polar_lipids', ''],
        area=600,
        udct=True,
    )
    MX = bst.Mixer(400, [thick_vinasse, condensate], vinasse)
    oil, polar_lipids, wastewater = oil_pretreatment_sys.outs
    
    # Fresh degummed oil
    transesterification_and_biodiesel_separation_sys, tbdct = create_transesterification_and_biodiesel_separation_system(
        ins=oil, 
        outs=[biodiesel, crude_glycerol, ''],
        mockup=True,
        area=600,
        udct=True,
    )
    MX = bst.Mixer(600, [transesterification_and_biodiesel_separation_sys-2, wastewater], 'wastewater')

    ### Facilities ###
    s = f.stream
    u = f.unit
    MX2 = bst.Mixer(700,
        [polar_lipids, bagasse]
    )
    # Burn bagasse from conveyor belt
    bst.BoilerTurbogenerator(700,
        (MX2-0, '', 
         'boiler_makeup_water',
         'natural_gas',
         'FGD_lime',
         'boilerchems'),
        ('emissions', 'rejected_water_and_blowdown', 'ash_disposal'),
        boiler_efficiency=0.80,
        turbogenerator_efficiency=0.85
    )
    bst.CoolingTower(800)
    makeup_water_streams = (s.cooling_tower_makeup_water,
                            s.boiler_makeup_water)
    process_water_streams = (s.imbibition_water,
                             s.biodiesel_wash_water,
                             s.oil_wash_water,
                             s.rvf_wash_water,
                             *makeup_water_streams)
    makeup_water = bst.Stream('makeup_water', price=0.000254)
    MX = bst.Mixer(800, [evaporator_condensate_b], 'recycle_process_water')
    bst.ChilledWaterPackage(800)
    bst.ProcessWaterCenter(800,
        (MX-0, makeup_water),
        (),
        None,
        makeup_water_streams,
        process_water_streams
    )
    HXN = bst.HeatExchangerNetwork(900, 
        ignored=lambda: [u.E301, u.D601.boiler, u.D602.boiler, u.H601, u.H602, u.H603, u.H604, oil_pretreatment_dct['F3']],
        Qmin=1e5,
    )
    HXN.acceptable_energy_balance_error = 0.01

@SystemFactory(
    ID='oilcane_sys',
    ins=[oilcane_dct],
    outs=[dict(ID='biodiesel', price=price['Biodiesel']),
          dict(ID='crude_glycerol', price=price['Crude glycerol'])],
)
def create_oilcane_to_biodiesel_combined_1_and_2g_post_fermentation_oil_separation(ins, outs):
    oilcane, = ins
    biodiesel, crude_glycerol = outs
    cofermentation = tmo.PRxn(
        [tmo.Rxn('CO2 + Xylose -> H2O + TAG', 'Xylose', 0.9500, correct_atomic_balance=True),
         tmo.Rxn('CO2 + Glucose -> H2O + TAG', 'Glucose', 0.9500, correct_atomic_balance=True)],
    )
    oilcane_to_fermentation_sys = create_cane_to_combined_1_and_2g_fermentation('oilcane_to_fermentation_sys',
        ins=oilcane, 
        product_group='Lipid',
        titer=89.4,
        productivity=0.61,
        cofermentation_reactions=cofermentation,
        seed_train_reactions=cofermentation,
        CoFermentation=units.CoFermentation,
        SeedTrain=units.SeedTrain,
    )
    beer, lignin, condensate, pretreatment_wastewater, fiber_fines = oilcane_to_fermentation_sys.outs
    post_fermentation_oil_separation_sys, pfls_dct = create_post_fermentation_oil_separation_system(
        ins=beer,
        mockup=True,
        area=600,
        udct=True,
        separate_cellmass=True,
    )
    backend_oil, cellmass, wastewater, evaporator_condensate = post_fermentation_oil_separation_sys.outs
    backend_oil.ID = 'backend_oil'
    MX_process_water = bst.Mixer(900, (condensate, evaporator_condensate),
                                 'recycle_process_water')
    oil_pretreatment_sys, oil_pretreatment_dct = create_oil_pretreatment_system(
        ins=backend_oil,
        outs=['', 'polar_lipids', ''],
        mockup=True,
        area=800,
        udct=True
    )
    oil, polar_lipids, wastewater_small = oil_pretreatment_sys.outs
    
    transesterification_and_biodiesel_separation_sys = create_transesterification_and_biodiesel_separation_system(
        ins=oil, 
        outs=[biodiesel, crude_glycerol, ''],
        mockup=True,
        area=800,
    )
    wastewater_treatment_sys = bst.create_wastewater_treatment_system(
        ins=[wastewater,
             fiber_fines,
             pretreatment_wastewater,
             wastewater_small,
             transesterification_and_biodiesel_separation_sys-2,
             evaporator_condensate],
        mockup=True,
        area=500,
    )
    s = f.stream
    u = f.unit
    M501 = bst.Mixer(700, (wastewater_treatment_sys-1, lignin, polar_lipids, cellmass, f.stream.filter_cake))
    brf.cornstover.create_facilities(
        solids_to_boiler=M501-0,
        gas_to_boiler=wastewater_treatment_sys-0,
        process_water_streams=(s.imbibition_water,
                               s.biodiesel_wash_water,
                               s.oil_wash_water,
                               s.rvf_wash_water,
                               s.caustic, 
                               s.warm_process_water,
                               s.pretreatment_steam,
                               s.saccharification_water),
        feedstock=s.bagasse,
        RO_water=wastewater_treatment_sys-2,
        recycle_process_water=MX_process_water-0,
        BT_area=700,
        area=900,
    )
    HXN = bst.HeatExchangerNetwork(1000,
        ignored=lambda: [u.D801.boiler, u.D802.boiler, u.H803, u.H802, u.H801, u.H804, u.H806, u.H809, oil_pretreatment_dct['F3']],
        Qmin=1e3,
    )
    HXN.acceptable_energy_balance_error = 0.01