"""
More detailed diagnostic - test the exact function used by the dashboard.
"""

import sys
sys.path.append('/Users/aidan/Desktop/tradev3')

from logic.iv import fetch_iv_context

def test_dashboard_iv_fetch():
    """Test the exact function the dashboard uses."""
    
    print("=" * 60)
    print("TESTING DASHBOARD IV FETCH FUNCTION")
    print("=" * 60)
    
    # Use a realistic SPY price
    reference_price = 600.0
    
    print(f"Calling fetch_iv_context('SPY', {reference_price})")
    print()
    
    try:
        result = fetch_iv_context('SPY', reference_price)
        
        print("RESULT:")
        print("-" * 60)
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        print()
        print("ANALYSIS:")
        print("-" * 60)
        
        atm_iv = result.get('atm_iv')
        vix_level = result.get('vix_level')
        
        print(f"  atm_iv is None: {atm_iv is None}")
        print(f"  vix_level is None: {vix_level is None}")
        
        if atm_iv is None or vix_level is None:
            print()
            print("⚠️  This would trigger 'Volatility context unavailable'")
            print()
            if atm_iv is None:
                print("  Reason: atm_iv is None")
            if vix_level is None:
                print("  Reason: vix_level is None")
        else:
            print()
            print("✓ Both values exist - should NOT show 'unavailable'")
            
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    test_dashboard_iv_fetch()

