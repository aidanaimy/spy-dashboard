"""
Test VIX fetch specifically to see if it's failing.
"""

import yfinance as yf

print("Testing VIX fetch...")
print("=" * 60)

try:
    vix = yf.Ticker("^VIX")
    print("✓ Created VIX ticker")
    
    hist = vix.history(period="252d")
    print(f"✓ Fetched history: {len(hist)} days")
    
    if not hist.empty:
        vix_level = float(hist['Close'].iloc[-1])
        print(f"✓ VIX Level: {vix_level:.2f}")
    else:
        print("✗ History is empty!")
        
except Exception as e:
    print(f"✗ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print("=" * 60)

