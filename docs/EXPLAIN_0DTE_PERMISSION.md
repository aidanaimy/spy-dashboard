# How 0DTE Permission Works (With VIX >= 15 Filter)

## The Logic Flow

The `get_0dte_permission()` function in `logic/regime.py` determines if it's safe to trade 0DTE options. Here's how it works:

### Step 1: VIX Hard Deck (HIGHEST PRIORITY)
```python
if vix_level is not None and vix_level <= 15:
    return 'AVOID'  # Too calm for options
```

**This is checked FIRST.** If VIX ≤ 15, immediately return `AVOID` regardless of anything else.

### Step 2: Gap + Range Chop Check
```python
if gap_abs < 0.2% and range_pct < 0.5%:
    return 'AVOID'  # Likely chop
```

Small gap AND low range = choppy day, avoid.

### Step 3: High Range = Favorable
```python
if range_pct > 1.5%:
    return 'FAVORABLE'  # Volatile day
```

If the day has high intraday range (>1.5%), it's volatile enough for 0DTE.

### Step 4: Default = Caution
```python
return 'CAUTION'  # Mixed conditions
```

Everything else gets CAUTION.

## The Complete Decision Tree

```
Is VIX available?
├─ YES: Is VIX <= 15?
│   ├─ YES → AVOID (too calm)
│   └─ NO → Continue to next check
└─ NO (VIX is None) → Continue to next check

Is gap < 0.2% AND range < 0.5%?
├─ YES → AVOID (chop)
└─ NO → Continue

Is range > 1.5%?
├─ YES → FAVORABLE (volatile)
└─ NO → CAUTION (mixed)
```

## Examples

### Example 1: High VIX, High Range
- VIX = 25
- Gap = 0.5%
- Range = 2.0%

**Result:** `FAVORABLE` ✅
- VIX > 15 ✓
- Not chop ✓
- Range > 1.5% ✓

### Example 2: Low VIX, High Range
- VIX = 12
- Gap = 0.5%
- Range = 2.0%

**Result:** `AVOID` ❌
- VIX ≤ 15 → **HARD STOP**
- (Doesn't matter that range is high)

### Example 3: High VIX, Low Range
- VIX = 20
- Gap = 0.3%
- Range = 0.8%

**Result:** `CAUTION` ⚠️
- VIX > 15 ✓
- Not chop (gap is 0.3%, not < 0.2%) ✓
- Range is NOT > 1.5% → CAUTION

### Example 4: VIX Unknown, High Range
- VIX = None
- Gap = 0.5%
- Range = 2.0%

**Result:** `FAVORABLE` ✅
- VIX check skipped (None)
- Not chop ✓
- Range > 1.5% ✓

### Example 5: High VIX, Choppy
- VIX = 20
- Gap = 0.1%
- Range = 0.4%

**Result:** `AVOID` ❌
- VIX > 15 ✓
- Gap < 0.2% AND range < 0.5% → **CHOP DETECTED**

## Impact on Options Trading

When `options_mode=True` (which backtests use), the signal generator requires:

1. **0DTE Permission = FAVORABLE** (not CAUTION or AVOID)
2. **Confidence = HIGH** (not MEDIUM or LOW)
3. **Minimum 1% move** (abs(return_5) >= 0.01)
4. **Minimum 12% IV** (if available)

So with the VIX ≤ 15 filter:
- **VIX ≤ 15 days:** Always AVOID → **No trades**
- **VIX > 15 + low range:** CAUTION → **No trades**
- **VIX > 15 + high range:** FAVORABLE → **Trades allowed** (if other conditions met)

## Historical VIX Distribution

Based on recent data (250 trading days):
- **VIX ≤ 15:** 11.2% of days (28 days)
- **VIX > 15:** 88.8% of days (222 days)

Of the 222 days with VIX > 15:
- Need **range > 1.5%** for FAVORABLE
- Estimate ~40-60% of days have range > 1.5%
- **Expected FAVORABLE days:** ~90-130 days per year

## Why This Matters

Before the VIX fix:
- VIX was returning `None` for all historical dates
- Days defaulted to CAUTION or AVOID based only on gap/range
- Most days didn't have range > 1.5%, so got CAUTION
- Options mode blocked all CAUTION days
- **Result: 0 trades**

After the VIX fix:
- VIX data flows correctly
- VIX > 15 days can get FAVORABLE (if range is also high)
- Options mode allows FAVORABLE days
- **Result: Should see 50-100+ trades over 2 years**
