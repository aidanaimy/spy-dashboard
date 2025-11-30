"""
Black-Scholes option pricing and Greeks calculations.
Used for options-aware backtesting and dashboard display.
"""

import math
from scipy.stats import norm
from typing import Dict, Optional
import numpy as np


def black_scholes_price(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
    """
    Calculate Black-Scholes option price.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free interest rate (annual)
        sigma: Implied volatility (annual)
        option_type: 'call' or 'put'
        
    Returns:
        Option price
    """
    if T <= 0:
        # At expiration, intrinsic value only
        if option_type == 'call':
            return max(S - K, 0)
        else:
            return max(K - S, 0)
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:  # put
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return max(price, 0)  # Can't be negative


def calculate_delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
    """
    Calculate option Delta (price sensitivity to underlying).
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free interest rate (annual)
        sigma: Implied volatility (annual)
        option_type: 'call' or 'put'
        
    Returns:
        Delta value
    """
    if T <= 0:
        # At expiration
        if option_type == 'call':
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    
    if option_type == 'call':
        return norm.cdf(d1)
    else:  # put
        return -norm.cdf(-d1)


def calculate_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option Gamma (Delta sensitivity to underlying).
    Same for calls and puts.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free interest rate (annual)
        sigma: Implied volatility (annual)
        
    Returns:
        Gamma value
    """
    if T <= 0:
        return 0.0
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return norm.pdf(d1) / (S * sigma * math.sqrt(T))


def calculate_theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
    """
    Calculate option Theta (time decay per day).
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free interest rate (annual)
        sigma: Implied volatility (annual)
        option_type: 'call' or 'put'
        
    Returns:
        Theta value (per day, negative for time decay)
    """
    if T <= 0:
        return 0.0
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    term1 = -S * norm.pdf(d1) * sigma / (2 * math.sqrt(T))
    
    if option_type == 'call':
        term2 = -r * K * math.exp(-r * T) * norm.cdf(d2)
    else:  # put
        term2 = r * K * math.exp(-r * T) * norm.cdf(-d2)
    
    # Convert from per year to per day (divide by 365)
    theta = (term1 + term2) / 365.0
    
    return theta


def calculate_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option Vega (IV sensitivity).
    Same for calls and puts.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free interest rate (annual)
        sigma: Implied volatility (annual)
        
    Returns:
        Vega value (per 1% IV change)
    """
    if T <= 0:
        return 0.0
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return S * norm.pdf(d1) * math.sqrt(T) / 100.0  # Per 1% IV change


def calculate_all_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> Dict[str, float]:
    """
    Calculate all Greeks for an option.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free interest rate (annual)
        sigma: Implied volatility (annual)
        option_type: 'call' or 'put'
        
    Returns:
        Dictionary with price, delta, gamma, theta, vega
    """
    price = black_scholes_price(S, K, T, r, sigma, option_type)
    delta = calculate_delta(S, K, T, r, sigma, option_type)
    gamma = calculate_gamma(S, K, T, r, sigma)
    theta = calculate_theta(S, K, T, r, sigma, option_type)
    vega = calculate_vega(S, K, T, r, sigma)
    
    return {
        'price': price,
        'delta': delta,
        'gamma': gamma,
        'theta': theta,
        'vega': vega
    }


def get_atm_strike(current_price: float, option_type: str = 'call', strike_spacing: float = 1.0) -> float:
    """
    Get at-the-money or slightly ITM strike price.
    - Call: Floor (round down) -> Slightly ITM
    - Put: Ceil (round up) -> Slightly ITM
    
    Args:
        current_price: Current stock price
        option_type: 'call' or 'put'
        strike_spacing: Strike spacing (default 1.0 for SPY)
        
    Returns:
        Selected strike price
    """
    if option_type.lower() == 'call':
        return math.floor(current_price / strike_spacing) * strike_spacing
    else:
        return math.ceil(current_price / strike_spacing) * strike_spacing


def time_to_expiration_0dte(current_time_hour: float, current_time_minute: float = 0) -> float:
    """
    Calculate time to expiration for 0DTE options (in years).
    0DTE options expire at 4:00 PM ET (16:00).
    
    Args:
        current_time_hour: Current hour (0-23)
        current_time_minute: Current minute (0-59)
        
    Returns:
        Time to expiration in years
    """
    expiration_hour = 16.0  # 4:00 PM ET
    current_time_decimal = current_time_hour + current_time_minute / 60.0
    
    if current_time_decimal >= expiration_hour:
        # After market close, next expiration is tomorrow
        hours_until_exp = 24 - current_time_decimal + expiration_hour
    else:
        hours_until_exp = expiration_hour - current_time_decimal
    
    # Convert hours to years (trading days: 252, hours per day: 6.5)
    return hours_until_exp / (252 * 6.5)


def calculate_option_pnl(entry_price: float, exit_price: float, contracts: int = 1, option_type: str = 'call') -> float:
    """
    Calculate P/L for an option trade.
    
    Args:
        entry_price: Option price at entry
        exit_price: Option price at exit
        contracts: Number of contracts (default 1)
        option_type: 'call' or 'put'
        
    Returns:
        P/L in dollars (per contract, multiplied by contracts)
    """
    # Each contract represents 100 shares
    pnl_per_contract = (exit_price - entry_price) * 100
    return pnl_per_contract * contracts

