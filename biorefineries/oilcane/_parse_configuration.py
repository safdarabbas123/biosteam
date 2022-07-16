# -*- coding: utf-8 -*-
"""
Created on Thu Nov  4 14:32:35 2021

@author: yrc2
"""
from typing import NamedTuple

__all__ = (
    'asconfiguration',
    'ascomparison',
    'Configuration',
    'ConfigurationComparison',
    'name_to_configuration',
    'parse',
    'format_name',
    'format_configuration',
    'format_comparison',
)

def asconfiguration(x):
    number, agile = x
    return Configuration(int(number), bool(agile))

def ascomparison(x):
    a, b = x
    return ConfigurationComparison(asconfiguration(a), asconfiguration(b))

class Configuration(NamedTuple):
    number: int
    agile: bool = False
   
class ConfigurationComparison(NamedTuple):
    a: Configuration
    b: Configuration

def name_to_configuration(name):
    name = name.replace(' ', '')
    return Configuration((-1 if name.startswith('S') else 1) * int(name[1]), '*' in name)

def parse(x):
    if isinstance(x, int):
        return Configuration(x)
    elif isinstance(x, str):
        x = x.upper()
        left, *right = x.split('-')
        if right:
            if len(right) == 1:
                right = right[0]
                return ConfigurationComparison(
                    name_to_configuration(left),
                    name_to_configuration(right)
                )
            else:
                raise RuntimeError('cannot parse multiple subtractions')
        else:
            factor = -1 if x.startswith('S') else 1
            return Configuration(factor * int(x[1]), '*' in x)
    elif isinstance(x, (Configuration, ConfigurationComparison)):
        return x
    else:
        try:
            try:
                return asconfiguration(x)
            except:
                return ascomparison(x)
        except:
            raise ValueError(f'could not parse {x}')
    
def format_name(name):
    key = parse(name)
    if isinstance(key, Configuration):
        return format_configuration(key)
    elif isinstance(key, ConfigurationComparison):
        return format_comparison(key)
    else:
        raise Exception('unknown error')

def format_configuration(configuration, latex=True):
    number, agile = configuration
    if number == -4:
        name = 'S4'
    elif number == -3:
        name = 'S3'
    if number == -2:
        name = 'S2'
    elif number == -1:
        name = 'S1'
    elif number == 0:
        name = '∅'
    elif number == 1:
        name = 'O1'
    elif number == 2:
        name = 'O2'
    elif number == 3:
        name = 'O3'
    elif number == 4:
        name = 'O4'
    elif number == 5:
        name = 'O5'
    elif number == 6:
        name = 'O6'
    else:
        raise ValueError(f'invalid configuration {configuration}')
    if latex:
        name = r'$\mathtt{' + name + '}$'
    if agile: name += '*'
    return name

def format_comparison(comparison):
    return ' $-$ '.join([format_configuration(i) for i in comparison])

