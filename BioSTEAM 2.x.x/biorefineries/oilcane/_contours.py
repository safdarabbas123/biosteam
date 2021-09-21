# -*- coding: utf-8 -*-
"""
Created on Fri Jun  4 23:44:10 2021

@author: yrc2
"""
from biorefineries import oilcane as oc
import biosteam as bst
import numpy as np
import pandas as pd
from biosteam.utils import colors
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
from biosteam.utils import colors
from biosteam.plots import (
    plot_contour_2d,
    MetricBar,
    plot_scatter_points,
    plot_contour_single_metric,
    plot_contour_1d,
    plot_vertical_line,
    rounded_tickmarks_from_data as tickmarks
)
from math import floor, ceil
from biosteam import plots
from biosteam.utils import CABBI_colors
from thermosteam.units_of_measure import format_units
from biosteam.plots.utils import style_axis, style_plot_limits, fill_plot, set_axes_labels
from biosteam import Metric
from warnings import filterwarnings
import os

__all__ = ('plot_extraction_efficiency_and_oil_content_contours',
           'plot_relative_sorghum_oil_content_and_cane_oil_content_contours',
           'plot_ethanol_and_biodiesel_price_contours')

filterwarnings('ignore', category=bst.utils.DesignWarning)
    
shadecolor = (*colors.neutral.RGBn, 0.20)
linecolor = (*colors.neutral_shade.RGBn, 0.85)
markercolor = (*colors.orange_tint.RGBn, 1)
edgecolor = (*colors.CABBI_black.RGBn, 1)
    
CABBI_colors = (colors.CABBI_yellow.tint(75).RGBn, 
                colors.CABBI_yellow.RGBn,
                colors.CABBI_green.RGBn,
                colors.CABBI_teal_green.shade(60).RGBn)

CABBI_colors_x = (colors.CABBI_blue_light.tint(90).RGBn,
                  colors.CABBI_blue_light.tint(40).RGBn, 
                  colors.CABBI_blue_light.RGBn, 
#                   colors.CABBI_teal.RGBn,
#                   colors.CABBI_teal_green.tint(10).RGBn,
                  colors.CABBI_teal_green.tint(40).shade(15).RGBn,
                  colors.CABBI_teal_green.shade(45).RGBn)

diverging_colormaps = [
    plt.cm.get_cmap('RdYlGn')
]

colormaps = [
    LinearSegmentedColormap.from_list('CABBI', CABBI_colors, 25),
    LinearSegmentedColormap.from_list('CABBI', CABBI_colors_x, 25),
    plt.cm.get_cmap('inferno_r'),
    plt.cm.get_cmap('copper_r'),
    plt.cm.get_cmap('bone_r'),
] * 2

def plot_ethanol_and_biodiesel_price_contours(N=30, benefit=False, cache={}, 
                                              enhanced_cellulosic_performance=False,
                                              titles=None):
    ethanol_price = np.linspace(1., 3., N)
    biodiesel_price = np.linspace(2, 6, N)
    oil_content = [5, 10, 15]
    N_rows = len(oil_content)
    configuration = ['O1', 'O2']
    N_cols = len(configuration)
    if (N, benefit, enhanced_cellulosic_performance) in cache:
        Z = cache[N, benefit, enhanced_cellulosic_performance]
    else:
        Z = np.zeros([N, N, N_rows, N_cols])
        for i in range(N_rows):
            for j in range(N_cols):
                oc.load(configuration[j], enhanced_cellulosic_performance=enhanced_cellulosic_performance)
                oc.set_cane_oil_content(oil_content[i])
                oc.set_relative_sorghum_oil_content(0)
                oc.sys.simulate()
                X, Y = np.meshgrid(ethanol_price, biodiesel_price)
                if benefit:
                    Z[:, :, i, j] = oc.evaluate_MFPP_benefit_across_ethanol_and_biodiesel_prices(X, Y)
                else:
                    Z[:, :, i, j] = oc.evaluate_MFPP_across_ethanol_and_biodiesel_prices(X, Y)
    xlabel = f"Ethanol price\n[{format_units('$/gal')}]"
    ylabels = [f"Biodiesel price\n[{format_units('$/gal')}]"] * 4
    xticks = [1., 1.5, 2.0, 2.5, 3.0]
    yticks = [2, 3, 4, 5, 6]
    marks = tickmarks(Z, 5, 5, center=0.) if benefit else tickmarks(Z, 5, 5)
    colormap = (diverging_colormaps if benefit else colormaps)[0]
    metric_bar = MetricBar('MFPP', format_units('$/ton'), colormap, marks, 12,
                           center=0.)
    if benefit:
        baseline = ['S1', 'S2']
        if titles is None:
            titles = [f"{oc.format_name(i)} - {oc.format_name(j)}"
                      for i, j in  zip(configuration, baseline)]
    elif titles is None:
        titles = [oc.format_name(i) for i in configuration]
    fig, axes, CSs, CB = plot_contour_single_metric(
        X, Y, Z, xlabel, ylabels, xticks, yticks, metric_bar, 
        fillblack=False, styleaxiskw=dict(xtick0=False), label=True,
        titles=titles,
    )
    for i in range(N_rows):
        for j in range(N_cols):
            ax = axes[i, j]
            CS = CSs[i, j]
            plt.sca(ax)
            data = Z[:, :, i, j]
            lb = data.min()
            ub = data.max()
            levels = [i for i in CS.levels if lb <= i <= ub]
            CS = plt.contour(X, Y, data=data, zorder=1e16, linestyles='dashed', linewidths=1.,
                             levels=levels, colors=[linecolor])
            ax.clabel(CS, levels=CS.levels, inline=True, fmt=lambda x: f'{round(x):,}',
                      fontsize=10, colors=[linecolor], zorder=1e16)

    plt.show()
    
def relative_sorghum_oil_content_and_cane_oil_content_data(load, relative):
    # Generate contour data
    y = np.linspace(0.05, 0.15, 20)
    x = np.linspace(-0.03, 0., 20) if relative else np.linspace(0.02, 0.15, 20)
    X, Y = np.meshgrid(x, y)
    folder = os.path.dirname(__file__)
    file = 'oil_content_analysis.npy'
    if relative: file = 'relative_' + file
    file = os.path.join(folder, file)
    configurations = [1, 2]
    if load:
        data = np.load(file)
    else:
        data = oc.evaluate_configurations_across_sorghum_and_cane_oil_content(
            X, Y, configurations, relative,
        )
    np.save(file, data)
    return X, Y, data
    
def plot_relative_sorghum_oil_content_and_cane_oil_content_contours(
        load=False, configuration_index=0, relative=False
    ):
    # Generate contour data
    X, Y, data = relative_sorghum_oil_content_and_cane_oil_content_data(load, relative)
    
    data = data[:, :, configuration_index, [0, 5]]
    
    # Plot contours
    xlabel = "Sorghum oil content\n[dry wt. %]" 
    if relative: xlabel = ('relative ' + xlabel).capitalize()
    ylabel = 'Cane oil content\n[dry wt. %]'
    yticks = [5, 7.5, 10, 12.5, 15]
    xticks = [-3, -2, -1, 0] if relative else [2, 5, 7.5, 10, 12.5, 15]
    MFPP = oc.all_metric_mockups[0]
    TCI = oc.all_metric_mockups[5]
    if configuration_index == 0:
        Z = np.array(["AGILE-CONVENTIONAL"])
        data = data[:, :, :, np.newaxis]
    elif configuration_index == 1:
        Z = np.array(["AGILE-CELLULOSIC"])
        data = data[:, :, :, np.newaxis]
    elif configuration_index == ...:
        Z = np.array(["AGILE-CONVENTIONAL", "AGILE-CELLULOSIC"])
        data = np.swapaxes(data, 2, 3)
    else:
        raise ValueError('configuration index must be either 0 or 1')
    metric_bars = [
        MetricBar(MFPP.name, format_units(MFPP.units), colormaps[0], tickmarks(data[:, :, 0], 5, 5), 20, 1),
        MetricBar(TCI.name, format_units(MFPP.units), colormaps[1], tickmarks(data[:, :, 1], 5, 5), 20)
    ]
    fig, axes, CSs, CB = plot_contour_2d(
        100.*X, 100.*Y, Z, data, xlabel, ylabel, xticks, yticks, metric_bars, 
        fillblack=False, styleaxiskw=dict(xtick0=True), label=True,
    )
    plt.show()
    
def plot_extraction_efficiency_and_oil_content_contours(load=False, metric_index=0):
    # Generate contour data
    x = np.linspace(0.4, 1., 20)
    y = np.linspace(0.05, 0.15, 20)
    X, Y = np.meshgrid(x, y)
    metric = bst.metric
    folder = os.path.dirname(__file__)
    file = 'oil_extraction_analysis.npy'
    file = os.path.join(folder, file)
    configurations = [1, 2]
    agile = [False, True]
    if load:
        data = np.load(file)
    else:
        data = oc.evaluate_configurations_across_extraction_efficiency_and_oil_content(
            X, Y, 0.70, agile, configurations, 
        )
    np.save(file, data)
    data = data[:, :, :, :, metric_index]
    
    # Plot contours
    xlabel = 'Oil extraction [%]'
    ylabel = "Oil content [dry wt. %]"
    ylabels = [f'Oilcane only\n{ylabel}',
               f'Oilcane & oilsorghum\n{ylabel}']
    xticks = [40, 60, 80, 100]
    yticks = [5, 7.5, 10, 12.5, 15]
    metric = oc.all_metric_mockups[metric_index]
    units = metric.units if metric.units == '%' else format_units(metric.units)
    metric_bar = MetricBar(metric.name, units, colormaps[metric_index], tickmarks(data, 5, 5), 18)
    fig, axes, CSs, CB = plot_contour_single_metric(
        100.*X, 100.*Y, data, xlabel, ylabels, xticks, yticks, metric_bar, 
        fillblack=False, styleaxiskw=dict(xtick0=False), label=True,
        titles=['CONVENTIONAL', 'CELLULOSIC'],
    )
    M = len(configurations)
    N = len(agile)
    for i in range(N):
        for j in range(M):
            ax = axes[i, j]
            CS = CSs[i, j]
            plt.sca(ax)
            metric_data = data[:, :, i, j]
            lb = metric_data.min()
            ub = metric_data.max()
            levels = [i for i in CS.levels if lb <= i <= ub]
            CS = plt.contour(100.*X, 100.*Y, data=metric_data, zorder=1e16, linestyles='dashed', linewidths=1.,
                             levels=levels, colors=[linecolor])
            ax.clabel(CS, levels=CS.levels, inline=True, fmt=lambda x: f'{round(x):,}',
                      fontsize=10, colors=[linecolor], zorder=1e16)
            if j == 0:
                lb = 60.0
                ub = 80.0
            else:
                lb = 70.0
                ub = 90.0
            plt.fill_between([lb, ub], [2], [20], 
                             color=shadecolor,
                             linewidth=1)
            plot_vertical_line(lb, ls='-.',
                               color=linecolor,
                               linewidth=1.0)
            plot_vertical_line(ub, ls='-.',
                               color=linecolor,
                               linewidth=1.0)
            # plot_scatter_points([lb], [5], marker='v', s=125, color=markercolor,
            #                     edgecolor=edgecolor)
            # plot_scatter_points([ub], [15], marker='^', s=125, color=markercolor,
            #                     edgecolor=edgecolor)

    plt.show()