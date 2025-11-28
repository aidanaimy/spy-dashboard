# 🧪 Tests Directory

This directory contains test scripts for validating system components.

## Test Scripts

### **test_discord.py**
Tests Discord webhook connectivity and notification sending.

**Usage**:
```bash
python tests/test_discord.py
```

**What it tests**:
- Discord webhook URL configuration
- Notification message formatting
- Webhook delivery success

---

### **test_signal_notification.py**
Tests the signal notification logic in the main app.

**Usage**:
```bash
python tests/test_signal_notification.py
```

**What it tests**:
- Signal change detection
- Notification filtering (confidence, permission, time)
- Discord message formatting

---

### **test_alpaca.py**
Tests Alpaca API connectivity and data fetching.

**Usage**:
```bash
python tests/test_alpaca.py
```

**What it tests**:
- API authentication
- Historical data retrieval
- Real-time data access

---

### **test_alpaca_date_limits.py**
Tests Alpaca API date range limits for historical data.

**Usage**:
```bash
python tests/test_alpaca_date_limits.py
```

**What it tests**:
- Maximum historical data range
- Date format handling
- Data availability by timeframe

---

## Running All Tests

```bash
# From project root
cd /Users/aidan/Desktop/tradev3

# Run individual tests
python tests/test_discord.py
python tests/test_alpaca.py

# Or run all tests (if you add a test runner)
python -m pytest tests/
```

---

## Adding New Tests

When adding new test scripts:
1. Name them `test_*.py`
2. Add a docstring explaining what it tests
3. Update this README with usage instructions
4. Ensure they can run from project root

