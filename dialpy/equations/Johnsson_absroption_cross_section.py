#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python3 functions for calculating CO2 concentration from DIAL measurements.

Created 2020-04-20
Antti J Manninen
Finnish Meteorological Institute
"""

import numpy as np
import pandas as pd
from scipy.integrate import quad
from dialpy.utilities import general_utils as gu
from dialpy.equations import constants

temperature = 293  # (K) = 20 celsius


def read_hitran_data(nu_):

    data = pd.read_csv(constants.PATH_TO_HITRAN, delimiter='\t', header=None)

    # Columns:  Isotopologue nu S A gamma_air gamma_self E" n_air delta_air J' J"
    idx, _ = gu.find_nearest(np.array(data.values[:, 1]), nu_)
    nu_0 = data.values[idx, 1]
    S_0 = data.values[idx, 2]
    gamma_0 = data.values[idx, 5] / 1e2  # (m / 1 atm)
    E_ = data.values[idx, 6] / 1e2
    a_ = data.values[idx, 7]

    return nu_0, S_0, gamma_0, E_, a_


def line_intensity(S_0, T_0, T_, h_, c_, nu_0, k_, E_):
    """See Johnson et al. (2013) Eq. (4) http://dx.doi.org/10.1364/AO.52.002994,
    and Browell et al. (1991) Eq. (1) https://doi.org/10.1364/AO.30.001517

    Args:
        S_0 (float): line strength (intensity) at temperature T_0 = 296,15 (K)
        T_0 (float): absolute reference temperature, 296,15 (K)
        T_ (float): temperature (K)
        h_ (float): Planck's constant
        c_ (float): speed of light
        nu_0 (float): wavenumber (central) at T_0 = 296,15 (K) and P_0 = 101325 (Pa)
        k_ (float): Boltzmann's constant
        E_ (float): lower energy state of the transition

    Returns:
        S_: line intensity

    """

    S_ = S_0 * (T_0/T_)**(3/2) * \
         ((1 - np.exp(-h_ * c_ * nu_0 / (k_ * T_))) / (1 - np.exp(-h_ * c_ * nu_0 / (k_ * T_0)))) * \
         np.exp((h_ * c_) / k_ * (1 / T_0 - 1 / T_) * E_)

    return S_


def pressure_broadened_linewidth(gamma_0, P_, P_0, T_0, T_, a_):
    """See Browell et al. (1991) Eq. (2) https://doi.org/10.1364/AO.30.001517

    Args:
        gamma_0: Lorentz linewidth at temperature T_0 = 296,15 (K) and pressure P_0 = 101325 (Pa)
        P_ (float): pressure (Pa)
        P_0: (float) standard atmosphere 101325 (Pa)
        T_0: (float) absolute reference temperature,296,15 (K)
        T_: (float) temperature (K)
        a_: (float) linewidth temperature-dependence parameter

    Returns:
        gamma_L: (float) pressure broadened linewidth at temperature T_ and pressure P_

    """

    gamma_L = gamma_0 * (P_ / P_0) * (T_0 / T_)**a_

    return gamma_L


def doppler_broadened_linewidth(nu_0, c_, k_, T_, m_):
    """Half-width at half maximum (HWHM), see See Johnson et al. (2013) p. 2996 http://dx.doi.org/10.1364/AO.52.002994,
    and Browell et al. (1991) p. 1518 https://doi.org/10.1364/AO.30.001517

    Args:
        nu_0: (float) wavenumber (central) at T_0 = 296,15 (K) and P_0 = 101325 (Pa)
        c_: (float) speed of light
        k_: (float) Boltzmann's constant
        T_: (float) temperature (K)
        m_: (float) mass of molecule (carbon dioxide in the case of CO2-DIAL)

    Returns:
        gamma_D: (float) Doppler broadened linewidth (HWHM)

    """

    gamma_D = (nu_0 / c_) * (2 * k_ * T_ * np.log(2) / m_)**(1/2)

    return gamma_D


def integrand(t, x, y):
    """Integrand function for integral calculated in the absorption cross section function

    Args:
        t: (float) variable of integration
        x: (float) (gamma_L / gamma_D)**2 * np.log(2)
        y: (float) ((nu-nu_0)/gamma_D) * np.log(2)**(1/2)

    Returns:

    """

    return np.exp(-t**2) / (x+(y-t)**2)


def absorption_cross_section(S_, gamma_L, gamma_D, nu, nu_0):
    """

    Args:
        S_: (float) line intensity
        gamma_L: (float) pressure broadened linewidth at temperature T_ and pressure P_
        gamma_D: (float) Doppler broadened linewidth (HWHM)
        nu: (float) wavenumber at which the cross section is being calculated
        nu_0: (float) wavenumber (central) at T_0 = 296,15 (K) and P_0 = 101325 (Pa)

    Returns:
        sigma_abs: (float) absorption cross section

    """

    x = (gamma_L / gamma_D)**2 * np.log(2)
    y = ((nu-nu_0) / gamma_D) * np.log(2)**(1/2)
    sigma_abs = S_ * (np.log(2) / np.pi**(3/2)) * (gamma_L / gamma_D**2) * quad(integrand, -np.inf, np.inf,
                                                                                args=(x, y))[0]

    return sigma_abs


def delta_absorption_cross_section(T_, P_):
    """

    Args:
        T_:
        P_:

    Returns:

    """

    nu_ON = 1 / constants.LAMBDA_ON
    nu_OFF = 1 / constants.LAMBDA_OFF
    nu_0_ON, S_0_ON, gamma_0_ON, E_ON, a_ON = read_hitran_data(nu_ON)
    nu_0_OFF, S_0_OFF, gamma_0_OFF, E_OFF, a_OFF = read_hitran_data(nu_OFF)
    T_0 = constants.REFERENCE_ABS_TEMPERATURE
    h_ = constants.PLANCKS_CONSTANT
    k_ = constants.BOLTZMANNS_CONSTANT_erg
    c_ = constants.SPEED_OF_LIGHT
    P_0 = constants.STANDARD_PRESSURE
    m_ = constants.MOLECULAR_MASS_CO2

    S_ON = line_intensity(S_0_ON, T_0, T_, h_, c_, nu_0_ON, k_, E_ON)
    S_OFF = line_intensity(S_0_OFF, T_0, T_, h_, c_, nu_0_OFF, k_, E_OFF)
    gamma_L_ON = pressure_broadened_linewidth(gamma_0_ON, P_, P_0, T_0, T_, a_ON)
    gamma_L_OFF = pressure_broadened_linewidth(gamma_0_OFF, P_, P_0, T_0, T_, a_OFF)
    gamma_D_ON = doppler_broadened_linewidth(nu_0_ON, c_, k_, T_, m_)
    gamma_D_OFF = doppler_broadened_linewidth(nu_0_OFF, c_, k_, T_, m_)
    sigma_abs_ON = absorption_cross_section(S_ON, gamma_L_ON, gamma_D_ON, nu_ON, nu_0_ON)
    sigma_abs_OFF = absorption_cross_section(S_OFF, gamma_L_OFF, gamma_D_OFF, nu_OFF, nu_0_OFF)

    return sigma_abs_ON - sigma_abs_OFF
