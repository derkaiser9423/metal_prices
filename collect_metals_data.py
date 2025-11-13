import requests
import sqlite3
import json
from datetime import datetime
import os
import sys

# Configuration
API_KEY = os.environ.get('GOLDAPI_KEY', 'goldapi-7lvv50smhqzls5q-io')
DB_PATH = 'metals_data.db'
METALS = ['XAU', 'XAG', 'XPT']  # Gold, Silver, Platinum
CURRENCY = 'USD'

# API Limit Management (100 requests/month = ~3 per day)
# With 3 metals, we can run once per day to stay under limit
API_REQUESTS_TABLE = 'api_requests_log'

def init_database():
    """Initialize SQLite database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metal_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            metal_symbol TEXT NOT NULL,
            currency TEXT NOT NULL,
            price REAL NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            change REAL,
            change_percent REAL,
            price_gram_24k REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(timestamp, metal_symbol, currency)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_metal_timestamp 
        ON metal_prices(metal_symbol, timestamp)
    ''')
    
    # Table to track API usage
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_requests_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_date TEXT NOT NULL,
            metal_symbol TEXT NOT NULL,
            success INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_request_date 
        ON api_requests_log(request_date)
    ''')
    
    conn.commit()
    conn.close()
    print(f"✓ Database initialized: {DB_PATH}")

def fetch_metal_price(symbol, currency, date=''):
    """Fetch metal price from GoldAPI."""
    url = f"https://www.goldapi.io/api/{symbol}/{currency}{date}"
    headers = {
        "x-access-token": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Log successful API request
        log_api_request(symbol, success=True)
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching {symbol}/{currency}: {str(e)}")
        
        # Log failed API request
        log_api_request(symbol, success=False)
        
        return None

def log_api_request(symbol, success):
    """Log API request to track usage."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        cursor.execute('''
            INSERT INTO api_requests_log (request_date, metal_symbol, success)
            VALUES (?, ?, ?)
        ''', (today, symbol, 1 if success else 0))
        conn.commit()
    except sqlite3.Error as e:
        print(f"✗ Error logging API request: {str(e)}")
    finally:
        conn.close()

def get_api_usage_stats():
    """Get API usage statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Current month usage
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute('''
        SELECT COUNT(*) FROM api_requests_log 
        WHERE request_date LIKE ? AND success = 1
    ''', (f'{current_month}%',))
    
    month_usage = cursor.fetchone()[0]
    
    # Today's usage
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*) FROM api_requests_log 
        WHERE request_date = ? AND success = 1
    ''', (today,))
    
    today_usage = cursor.fetchone()[0]
    
    conn.close()
    
    return month_usage, today_usage

def check_rate_limit():
    """Check if we're within rate limits."""
    month_usage, today_usage = get_api_usage_stats()
    
    # 100 requests/month limit, leave buffer of 5
    MONTHLY_LIMIT = 95
    # Maximum 3 requests per day (100/30 days)
    DAILY_LIMIT = 3
    
    print(f"\n📊 API Usage Stats:")
    print(f"   This month: {month_usage}/100 requests")
    print(f"   Today: {today_usage}/{DAILY_LIMIT} requests")
    
    if month_usage >= MONTHLY_LIMIT:
        print(f"⚠️  Monthly limit reached ({month_usage}/100). Skipping collection.")
        return False
    
    if today_usage >= DAILY_LIMIT:
        print(f"⚠️  Daily limit reached ({today_usage}/{DAILY_LIMIT}). Skipping collection.")
        return False
    
    remaining = min(MONTHLY_LIMIT - month_usage, DAILY_LIMIT - today_usage)
    print(f"✓ Safe to proceed. Can make {remaining} more request(s) today.\n")
    
    return True

def save_to_database(data, symbol, currency):
    """Save metal price data to database."""
    if not data:
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Convert Unix timestamp to ISO format
        timestamp = datetime.fromtimestamp(data.get('timestamp', 0)).isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO metal_prices 
            (timestamp, metal_symbol, currency, price, open_price, high_price, 
             low_price, change, change_percent, price_gram_24k)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            symbol,
            currency,
            data.get('price', 0),
            data.get('open_price', 0),
            data.get('high_price', 0),
            data.get('low_price', 0),
            data.get('ch', 0),
            data.get('chp', 0),
            data.get('price_gram_24k', 0)
        ))
        
        conn.commit()
        print(f"✓ Saved {symbol}/{currency}: ${data.get('price', 0):.2f}")
        return True
    except sqlite3.Error as e:
        print(f"✗ Database error for {symbol}/{currency}: {str(e)}")
        return False
    finally:
        conn.close()

def fetch_historical_data(symbol, currency, start_date, end_date):
    """Fetch historical data for a date range."""
    from datetime import datetime, timedelta
    
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    
    current = start
    success_count = 0
    
    while current <= end:
        date_str = current.strftime('%Y%m%d')
        print(f"Fetching {symbol} for {date_str}...")
        
        data = fetch_metal_price(symbol, currency, f'/{date_str}')
        if data and save_to_database(data, symbol, currency):
            success_count += 1
        
        current += timedelta(days=1)
    
    print(f"✓ Historical data fetch complete: {success_count} records saved")

def collect_current_prices():
    """Collect current prices for all configured metals."""
    print(f"\n{'='*60}")
    print(f"Collecting metal prices - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    init_database()
    
    # Check rate limits before proceeding
    if not check_rate_limit():
        print("\n⚠️  Skipping collection due to rate limits.")
        print("💡 Tip: Reduce collection frequency or upgrade API plan.\n")
        return False
    
    success_count = 0
    for metal in METALS:
        data = fetch_metal_price(metal, CURRENCY)
        if data and save_to_database(data, metal, CURRENCY):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"✓ Collection complete: {success_count}/{len(METALS)} metals updated")
    print(f"{'='*60}\n")
    
    return success_count > 0  # Return True if at least one succeeded

def get_latest_prices():
    """Display latest prices from database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\nLatest Prices:")
    print("-" * 60)
    
    for metal in METALS:
        cursor.execute('''
            SELECT timestamp, price, change, change_percent
            FROM metal_prices
            WHERE metal_symbol = ? AND currency = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (metal, CURRENCY))
        
        row = cursor.fetchone()
        if row:
            metal_names = {'XAU': 'Gold', 'XAG': 'Silver', 'XPT': 'Platinum'}
            name = metal_names.get(metal, metal)
            change_symbol = '+' if row[2] >= 0 else ''
            print(f"{name:10} ${row[1]:8.2f}  {change_symbol}{row[2]:6.2f} ({change_symbol}{row[3]:.2f}%)")
    
    conn.close()
    print("-" * 60)

if __name__ == "__main__":
    # Check for historical mode
    if len(sys.argv) == 4 and sys.argv[1] == '--historical':
        start_date = sys.argv[2]
        end_date = sys.argv[3]
        init_database()
        for metal in METALS:
            fetch_historical_data(metal, CURRENCY, start_date, end_date)
    else:
        # Normal operation: collect current prices
        success = collect_current_prices()
        get_latest_prices()
        sys.exit(0 if success else 1)
