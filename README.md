# 📊 Precious Metals Price Tracker

[![Collect Metals Data](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/actions/workflows/collect_data.yml/badge.svg)](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/actions/workflows/collect_data.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Data Source](https://img.shields.io/badge/Data-GoldAPI.io-gold)](https://www.goldapi.io/)

Automated collection and storage of real-time precious metals prices (Gold, Silver, Platinum) using GitHub Actions and SQLite database.

## 🌟 Features

- ⏰ **Automated daily data collection** via GitHub Actions (optimized for 100 req/month limit)
- 💾 **SQLite database** for historical price storage
- 📈 **Track multiple metals**: Gold (XAU), Silver (XAG), Platinum (XPT)
- 🔄 **Historical data import** capability
- 📊 **Price tracking**: Open, High, Low, Close, and % Change
- 🤖 **Zero maintenance** - runs automatically in the cloud
- 📉 **API usage tracking** - never exceed your rate limits

## 📦 Database Schema

The SQLite database stores comprehensive price information:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | TEXT | ISO timestamp of the price |
| `metal_symbol` | TEXT | Metal code (XAU/XAG/XPT) |
| `currency` | TEXT | Currency code (AUD) |
| `price` | REAL | Current price per Troy Ounce |
| `open_price` | REAL | Opening price |
| `high_price` | REAL | Daily high |
| `low_price` | REAL | Daily low |
| `change` | REAL | Absolute price change |
| `change_percent` | REAL | Percentage change |
| `price_gram_24k` | REAL | Price per gram (24K) |

### API Usage Tracking

The database also includes an `api_requests_log` table to monitor your API usage:

| Column | Type | Description |
|--------|------|-------------|
| `request_date` | TEXT | Date of the request (YYYY-MM-DD) |
| `metal_symbol` | TEXT | Metal code requested |
| `success` | INTEGER | 1 if successful, 0 if failed |
| `created_at` | TEXT | Timestamp of the request |

## ⚠️ API Rate Limit Management

**Important**: The free GoldAPI plan has a **100 requests/month limit**.

This script is configured to:
- ✅ Run **once per day** (3 metals × 30 days = 90 requests/month)
- ✅ Track all API usage in the database
- ✅ Check limits before making requests
- ✅ Leave a 5-request buffer for safety
- ✅ Skip collection if limits are reached

### Check Your API Usage

```bash
python collect_metals_data.py
# Output will show: "This month: X/100 requests"
```

### View Usage in Database

```sql
SELECT 
    strftime('%Y-%m', request_date) as month,
    COUNT(*) as total_requests,
    SUM(success) as successful_requests
FROM api_requests_log
GROUP BY month;
```

## 🚀 Setup Instructions

### 1. Fork/Clone this Repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 2. Add API Key as GitHub Secret

1. Go to your repository **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `GOLDAPI_KEY`
4. Value: `goldapi-7lvv50smhqzls5q-io` (or your own key)
5. Click **Add secret**

### 3. Enable GitHub Actions

1. Go to the **Actions** tab in your repository
2. Enable workflows if prompted
3. The workflow will run automatically every hour

### 4. Initial Database Setup

Commit an empty `.gitkeep` file or run the action manually once to create the initial database:

```bash
python collect_metals_data.py
git add metals_data.db
git commit -m "Initialize database"
git push
```

## 💻 Local Usage

### Install Dependencies

```bash
pip install requests
```

### Collect Current Prices

```bash
python collect_metals_data.py
```

### Import Historical Data

```bash
# Fetch data from January 1, 2024 to January 31, 2024
python collect_metals_data.py --historical 20240101 20240131
```

### View Latest Prices

```python
import sqlite3

conn = sqlite3.connect('metals_data.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT metal_symbol, price, change_percent, timestamp 
    FROM metal_prices 
    ORDER BY timestamp DESC 
    LIMIT 10
''')

for row in cursor.fetchall():
    print(f"{row[0]}: ${row[1]:.2f} ({row[2]:+.2f}%) - {row[3]}")

conn.close()
```

## 📊 Sample Queries

### Get Latest Gold Price

```sql
SELECT price, change_percent 
FROM metal_prices 
WHERE metal_symbol = 'XAU' 
ORDER BY timestamp DESC 
LIMIT 1;
```

### Calculate Average Daily Price

```sql
SELECT 
    DATE(timestamp) as date,
    metal_symbol,
    AVG(price) as avg_price,
    MIN(low_price) as day_low,
    MAX(high_price) as day_high
FROM metal_prices
GROUP BY DATE(timestamp), metal_symbol
ORDER BY date DESC;
```

### Track Price Changes Over Time

```sql
SELECT 
    timestamp,
    metal_symbol,
    price,
    LAG(price) OVER (PARTITION BY metal_symbol ORDER BY timestamp) as prev_price,
    price - LAG(price) OVER (PARTITION BY metal_symbol ORDER BY timestamp) as price_diff
FROM metal_prices
ORDER BY timestamp DESC;
```

## 🔧 Configuration

Edit `collect_metals_data.py` to customize:

```python
METALS = ['XAU', 'XAG', 'XPT']  # Add XPD for Palladium (but watch your API limits!)
CURRENCY = 'USD'                 # Change to EUR, GBP, AUD, etc.
```

**Note**: Adding more metals increases API usage. With 4 metals and daily collection, you'd use 120 requests/month (over limit!)

### Reducing API Usage

If you need to stay well under the limit:

1. **Track fewer metals**: Remove XPT to track only Gold & Silver (60 req/month)
2. **Less frequent runs**: Weekly schedule uses only 12 req/month
3. **Single metal focus**: Track only Gold for 30 req/month

```python
# Conservative option - only Gold, weekly
METALS = ['XAU']
# Cron: '0 9 * * 1'  # Every Monday
```

## 📅 Schedule

The GitHub Action runs:
- ⏰ **Once per day** at 9:00 AM UTC (safe for 100 req/month limit)
- 🖱️ **Manual trigger** via Actions tab (watch your limits!)
- 🔄 **On code changes** only (not data changes)

### Why Once Per Day?

With 3 metals and 100 requests/month:
- 100 requests ÷ 30 days = **3.3 requests/day maximum**
- 3 metals × 1 run/day = **3 requests/day** ✅
- Leaves buffer for manual runs and testing

### To Change Schedule

Edit `.github/workflows/collect_data.yml`:

```yaml
schedule:
  # Examples:
  - cron: '0 9 * * *'      # Daily at 9 AM UTC
  - cron: '0 0 * * 0'      # Weekly on Sunday (12 req/month)
  - cron: '0 9 1,15 * *'   # Twice a month (6 req/month)
```

**Warning**: Running hourly would use 2,160 requests/month and exhaust your limit in ~1 day!

## 📈 Data Visualization

You can export the database for analysis:

```bash
# Export to CSV
sqlite3 metals_data.db -header -csv "SELECT * FROM metal_prices;" > prices.csv
```

Then use tools like:
- 📊 Excel/Google Sheets
- 🐍 Python (pandas, matplotlib)
- 📉 Tableau/Power BI
- 📱 Grafana

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for informational purposes only. Precious metals prices are delayed and should not be used for trading decisions. Always consult with a financial advisor.

## 🔗 Resources

- [GoldAPI Documentation](https://www.goldapi.io/dashboard)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

## 📞 Support

If you encounter issues:

1. Check the [Actions tab](../../actions) for workflow logs
2. Verify your API key is correctly set in Secrets
3. Ensure the database file is being committed
4. Open an issue with error details

---

**Made with AI using GitHub Actions and GoldAPI**

**Last Updated**: Auto-updated daily at 9:00 AM UTC

**API Usage**: Optimized for free tier (100 requests/month)
