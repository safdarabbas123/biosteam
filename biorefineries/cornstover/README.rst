==============================================================
cornstover: 2nd Generation Ethanol Production from Corn Stover
==============================================================

.. figure:: ./images/cornstover_areas.png

The corn stover biorefinery design for the production of cellulosic ethanol 
follows all assumptions from a study by Humbird et. al. executed with Aspen 
plus [1]_. As discussed in the original BioSTEAM manuscript [2]_, the 
corn stover biorefinery can be divided into eight areas: feedstock handling, 
pretreatment and conditioning, enzyme production, recovery, wastewater 
treatment, storage, boiler and turbo-generator system, and utilities. In 
contrast to the original report by Humbird et al., the on-site enzyme 
production model is not included. Instead, the cellulase mixture is bought at 
the same concentration of 50 g·L–1 and at a price of 0.424 $·kg–1, which is 
the back-calculated cost of on-site enzyme production as reported in the 
benchmark study. During pretreatment, the corn stover is presteamed and 
loaded into pretreatment reactors with dilute sulfuric acid under high 
pressures and temperatures to break down the biomass and facilitate enzymatic 
hydrolysis (Area 200). The hydrolysate is then saccharified and fermented in 
the fermentation area (Area 300). In the recovery area, the beer is distilled, 
and the lignin-rich solid fraction is filter-pressed (Area 400). The stillage 
is sent to wastewater treatment to produce biogas (Area 500), while the lignin 
is sent to the boiler-turbo-generator section (Area 700) to produce steam and 
electricity.

Getting Started
---------------

To load the biorefinery, simply import it. All data and variables
are lazy loaded by the module:

.. code-block:: python

    >>> from biorefineries import cornstover as cs
    >>> # This is optional; it forces the biorefinery to load
    >>> # Otherwise, first time accessing will take a bit to load.
    >>> cs.load()
    >>> cs.chemicals # All chemicals used by the biorefinery.
    CompiledChemicals([Water, Ethanol, AceticAcid, Furfural, Glycerol, H2SO4, LacticAcid, SuccinicAcid, P4O10, HNO3, Denaturant, DAP, AmmoniumAcetate, AmmoniumSulfate, NaNO3, Oil, HMF, N2, NH3, O2, CH4, H2S, SO2, CO2, NO2, NO, CO, Glucose, Xylose, Sucrose, CaSO4, Mannose, Galactose, Arabinose, CellulaseNutrients, Extract, Acetate, Tar, CaO, Ash, NaOH, Lignin, SolubleLignin, GlucoseOligomer, GalactoseOligomer, MannoseOligomer, XyloseOligomer, ArabinoseOligomer, Z_mobilis, T_reesei, Biomass, Cellulose, Protein, Enzyme, Glucan, Xylan, Xylitol, Cellobiose, CSL, DenaturedEnzyme, Arabinan, Mannan, Galactan, WWTsludge, Cellulase])
    >>> cs.cornstover_sys.show() # The main biorefinery system
    System: cornstover_sys
    ins...
    [0] cornstover
        phase: 'l', T: 298.15 K, P: 101325 Pa
        flow (kmol/hr): Water     1.17e+03
                        Sucrose   1.9
                        Extract   68.5
                        Acetate   25.4
                        Ash       4.16e+03
                        Lignin    87.3
                        Protein   114
                        ...
    [1] denaturant
        phase: 'l', T: 298.15 K, P: 101325 Pa
        flow (kmol/hr): Denaturant  4.14
    outs...
    [0] ethanol
        phase: 'l', T: 339.28 K, P: 101325 Pa
        flow (kmol/hr): Water       9.84
                        Ethanol     463
                        Denaturant  4.14
    >>> cs.cornstover_tea.show() # The TEA object
    ellulosicEthanolTEA: cornstover_sys
     NPV: -190,889 USD at 10.0% IRR
    >>> cs.flowsheet # The complete flowsheet
    <Flowsheet: cornstover>
    >>> cs.R303.show() # Any unit operations and streams can be accessed through the module
    SaccharificationAndCoFermentation: R303
    ins...
    [0] slurry  from  ContinuousPresaccharification-R301
        phase: 'l', T: 321.15 K, P: 101325 Pa
        flow (kmol/hr): Water              1.9e+04
                        AceticAcid         19.5
                        Furfural           2.67
                        AmmoniumSulfate    18.3
                        HMF                2.45
                        Glucose            19.9
                        Xylose             112
                        ...
    [1] s23  from  SeedHoldTank-T301
        phase: 'l', T: 305.15 K, P: 101325 Pa
        flow (kmol/hr): Water              1.89e+03
                        Ethanol            44.9
                        AceticAcid         1.95
                        Furfural           0.267
                        Glycerol           0.189
                        SuccinicAcid       0.368
                        DAP                0.0825
                        ...
    [2] CSL2  from  MockSplitter-S302
        phase: 'l', T: 298.15 K, P: 101325 Pa
        flow (kmol/hr): CSL  28.9
    [3] DAP2  from  MockSplitter-S301
        phase: 'l', T: 298.15 K, P: 101325 Pa
        flow (kmol/hr): DAP  1.04
    outs...
    [0] s24  to  Mixer-M304
        phase: 'g', T: 305.15 K, P: 101325 Pa
        flow (kmol/hr): Water         15.3
                        Ethanol       3.95
                        AceticAcid    0.0306
                        Furfural      0.0134
                        Glycerol      1.52e-07
                        LacticAcid    9.36e-06
                        SuccinicAcid  2.47e-08
                        ...
    [1] s25  to  Mixer-M401
        phase: 'l', T: 305.15 K, P: 101325 Pa
        flow (kmol/hr): Water              1.89e+04
                        Ethanol            459
                        AceticAcid         19.5
                        Furfural           2.66
                        Glycerol           1.85
                        LacticAcid         18.4
                        SuccinicAcid       3.61
                        ...
    [2] s20  to  SeedTrain-R302
        phase: 'l', T: 321.15 K, P: 101325 Pa
        flow (kmol/hr): Water              1.89e+03
                        AceticAcid         1.95
                        Furfural           0.267
                        AmmoniumSulfate    1.83
                        HMF                0.245
                        Glucose            16.6
                        Xylose             11.2
                        ...


References
----------
.. [1] Humbird, D.; Davis, R.; Tao, L.; Kinchin, C.; Hsu, D.; Aden, A.; Schoen, 
    P.; Lukas, J.; Olthof, B.; Worley, M.; Sexton, D.; Dudgeon, D. Process 
    Design and Economics for Biochemical Conversion of Lignocellulosic Biomass 
    to Ethanol: Dilute-Acid Pretreatment and Enzymatic Hydrolysis of Corn 
    Stover, Technical Report NREL/TP-5100-47764; DOE: NREL, 2011.

.. [2] Cortes-Peña, Y.; Kumar, D.; Singh, V.; Guest, J. S.
    BioSTEAM: A Fast and Flexible Platform for the Design, Simulation, and 
    Techno-Economic Analysis of Biorefineries under Uncertainty. 
    ACS Sustainable Chem. Eng. 2020. https://doi.org/10.1021/acssuschemeng.9b07040.


