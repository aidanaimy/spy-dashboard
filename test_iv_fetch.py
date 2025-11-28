"""
Debug script to test IV data fetching and diagnose issues.
"""

import yfinance as yf
import numpy as np
from datetime import datetime

def test_iv_fetch():
    """Test fetching IV data and print detailed diagnostics."""
    
    print("=" * 60)
    print("IV DATA FETCH DIAGNOSTIC")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # Test 1: SPY Options Chain
    print("TEST 1: SPY Options Chain")
    print("-" * 60)
    try:
        ticker = yf.Ticker("SPY")
        print(f"✓ Created yfinance Ticker for SPY")
        
        # Get current price
        info = ticker.fast_info
        current_price = info.get('lastPrice', info.get('regularMarketPrice', 0))
        print(f"✓ Current SPY Price: ${current_price:.2f}")
        
        # Get available expirations
        options = ticker.options
        print(f"✓ Available Expirations: {len(options)} dates")
        if options:
            print(f"  First 5: {list(options[:5])}")
            
            # Get nearest expiration
            expiry = options[0]
            print(f"✓ Using Expiration: {expiry}")
            
            # Fetch option chain
            chain = ticker.option_chain(expiry)
            calls = chain.calls
            puts = chain.puts
            
            print(f"✓ Calls: {len(calls)} strikes")
            print(f"✓ Puts: {len(puts)} strikes")
            
            if not calls.empty and not puts.empty:
                # Find ATM strike
                call_idx = (calls['strike'] - current_price).abs().idxmin()
                put_idx = (puts['strike'] - current_price).abs().idxmin()
                
                atm_call_strike = calls.loc[call_idx, 'strike']
                atm_put_strike = puts.loc[put_idx, 'strike']
                atm_call_iv = float(calls.loc[call_idx, 'impliedVolatility'])
                atm_put_iv = float(puts.loc[put_idx, 'impliedVolatility'])
                
                print(f"\n  ATM Call Strike: ${atm_call_strike:.2f}")
                print(f"  ATM Call IV: {atm_call_iv*100:.2f}%")
                print(f"  ATM Put Strike: ${atm_put_strike:.2f}")
                print(f"  ATM Put IV: {atm_put_iv*100:.2f}%")
                
                atm_iv = np.mean([atm_call_iv, atm_put_iv]) * 100
                print(f"\n✓ FINAL ATM IV: {atm_iv:.2f}%")
                
                # Check if suspiciously low
                if atm_iv < 5:
                    print(f"⚠️  WARNING: ATM IV is suspiciously low!")
                    print(f"    This suggests stale or bad data.")
            else:
                print("✗ ERROR: Option chain is empty")
                
        else:
            print("✗ ERROR: No expirations available")
            
    except Exception as e:
        print(f"✗ ERROR fetching SPY options: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test 2: VIX Data
    print("TEST 2: VIX Index Data")
    print("-" * 60)
    try:
        vix = yf.Ticker("^VIX")
        print(f"✓ Created yfinance Ticker for ^VIX")
        
        # Fetch 252 days of history
        hist = vix.history(period="252d")
        print(f"✓ Fetched VIX History: {len(hist)} days")
        
        if not hist.empty:
            vix_level = float(hist['Close'].iloc[-1])
            vix_min = float(hist['Close'].min())
            vix_max = float(hist['Close'].max())
            
            print(f"✓ Current VIX Level: {vix_level:.2f}")
            print(f"  VIX Min (252d): {vix_min:.2f}")
            print(f"  VIX Max (252d): {vix_max:.2f}")
            
            if vix_max > vix_min:
                vix_rank = (vix_level - vix_min) / (vix_max - vix_min)
                print(f"✓ VIX Rank: {vix_rank*100:.0f}%")
            
            vix_percentile = float((hist['Close'] <= vix_level).mean())
            print(f"✓ VIX Percentile: {vix_percentile*100:.0f}%")
        else:
            print("✗ ERROR: VIX history is empty")
            
    except Exception as e:
        print(f"✗ ERROR fetching VIX data: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_iv_fetch()

