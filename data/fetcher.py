"""
Data fetcher with SQLite caching for historical OHLCV data.
"""
import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches and caches historical market data from Yahoo Finance."""
    
    def __init__(self, cache_db_path: str = "data/cache.db"):
        """Initialize the data fetcher with a cache database."""
        self.cache_db_path = Path(cache_db_path)
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_cache_db()
    
    def _init_cache_db(self):
        """Initialize the cache database schema."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_data (
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fetch_metadata (
                ticker TEXT PRIMARY KEY,
                last_fetch_date DATE,
                last_updated TIMESTAMP
            )
        """)
        
        # Ticker registry with company names
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticker_registry (
                ticker TEXT PRIMARY KEY,
                company_name TEXT,
                asset_type TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_validated TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def fetch_ticker_data(
        self, 
        ticker: str, 
        start_date: str, 
        end_date: str,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Fetch historical data for a ticker, using cache when possible.
        
        Args:
            ticker: Stock/ETF ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Adj Close, Volume
        """
        ticker = ticker.upper()
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Check cache first
        if not force_refresh:
            cached_data = self._get_cached_data(ticker, start_date, end_date)
            if cached_data is not None and len(cached_data) > 0:
                # Check if we have all required dates
                cached_dates = set(cached_data.index)
                required_dates = set(pd.date_range(start_dt, end_dt, freq='D'))
                missing_dates = required_dates - cached_dates
                
                if len(missing_dates) == 0:
                    logger.info(f"Using cached data for {ticker}")
                    return cached_data
        
        # Fetch missing data from Yahoo Finance
        logger.info(f"Fetching data for {ticker} from {start_date} to {end_date}")
        try:
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(start=start_date, end=end_date)
            
            if df.empty:
                raise ValueError(f"No data available for {ticker} in date range")
            
            # Standardize column names
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            df.index.name = 'date'
            df = df.reset_index()
            
            # Store in cache
            self._store_in_cache(ticker, df)
            
            # Get full range from cache (may include previously cached data)
            result = self._get_cached_data(ticker, start_date, end_date)
            return result
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            raise ValueError(f"Failed to fetch data for {ticker}: {str(e)}")
    
    def _get_cached_data(
        self, 
        ticker: str, 
        start_date: str, 
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Retrieve cached data for a ticker and date range."""
        conn = sqlite3.connect(self.cache_db_path)
        
        query = """
            SELECT date, open, high, low, close, adj_close, volume
            FROM price_data
            WHERE ticker = ? AND date >= ? AND date <= ?
            ORDER BY date
        """
        
        df = pd.read_sql_query(
            query, 
            conn, 
            params=(ticker, start_date, end_date),
            parse_dates=['date']
        )
        
        conn.close()
        
        if df.empty:
            return None
        
        df.set_index('date', inplace=True)
        return df
    
    def _store_in_cache(self, ticker: str, df: pd.DataFrame):
        """Store price data in the cache database."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        ticker = ticker.upper()
        
        for _, row in df.iterrows():
            date = row['date']
            if pd.isna(date):
                continue
                
            cursor.execute("""
                INSERT OR REPLACE INTO price_data 
                (ticker, date, open, high, low, close, adj_close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                date.strftime('%Y-%m-%d'),
                row.get('open'),
                row.get('high'),
                row.get('low'),
                row.get('close'),
                row.get('adj_close'),
                int(row.get('volume', 0)) if pd.notna(row.get('volume')) else None
            ))
        
        # Update fetch metadata
        cursor.execute("""
            INSERT OR REPLACE INTO fetch_metadata 
            (ticker, last_fetch_date, last_updated)
            VALUES (?, ?, ?)
        """, (
            ticker,
            df['date'].max().strftime('%Y-%m-%d'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def validate_tickers(self, tickers: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate that tickers exist and have data available.
        Caches ticker info (name, type) in registry.
        
        Returns:
            Tuple of (valid_tickers, invalid_tickers)
        """
        valid = []
        invalid = []
        
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        for ticker in tickers:
            ticker_upper = ticker.upper()
            
            # Check if already in registry
            cursor.execute("SELECT ticker FROM ticker_registry WHERE ticker = ?", (ticker_upper,))
            if cursor.fetchone():
                valid.append(ticker_upper)
                continue
            
            try:
                ticker_obj = yf.Ticker(ticker_upper)
                info = ticker_obj.info
                
                if info and 'symbol' in info:
                    # Extract company name and type
                    company_name = info.get('longName') or info.get('shortName') or info.get('name', ticker_upper)
                    asset_type = 'ETF' if 'etf' in info.get('quoteType', '').lower() else 'Stock'
                    
                    # Store in registry
                    cursor.execute("""
                        INSERT OR REPLACE INTO ticker_registry 
                        (ticker, company_name, asset_type, last_validated)
                        VALUES (?, ?, ?, ?)
                    """, (ticker_upper, company_name, asset_type, datetime.now().isoformat()))
                    
                    valid.append(ticker_upper)
                    logger.info(f"Validated and cached {ticker_upper}: {company_name} ({asset_type})")
                else:
                    invalid.append(ticker_upper)
            except Exception as e:
                logger.warning(f"Ticker {ticker} validation failed: {e}")
                invalid.append(ticker_upper)
        
        conn.commit()
        conn.close()
        
        return valid, invalid
    
    def get_ticker_info(self, ticker: str) -> Optional[dict]:
        """Get cached ticker information."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ticker, company_name, asset_type, first_seen, last_validated
            FROM ticker_registry WHERE ticker = ?
        """, (ticker.upper(),))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'ticker': row[0],
                'company_name': row[1],
                'asset_type': row[2],
                'first_seen': row[3],
                'last_validated': row[4]
            }
        return None
    
    def list_tickers(self) -> List[dict]:
        """List all discovered/validated tickers."""
        conn = sqlite3.connect(self.cache_db_path)
        
        query = """
            SELECT ticker, company_name, asset_type, first_seen, last_validated
            FROM ticker_registry
            ORDER BY company_name
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df.to_dict('records')
    
    def export_to_csv(self, ticker: str, output_path: str):
        """Export cached data for a ticker to CSV."""
        conn = sqlite3.connect(self.cache_db_path)
        
        query = """
            SELECT date, open, high, low, close, adj_close, volume
            FROM price_data
            WHERE ticker = ?
            ORDER BY date
        """
        
        df = pd.read_sql_query(
            query, 
            conn, 
            params=(ticker.upper(),),
            parse_dates=['date']
        )
        
        conn.close()
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {ticker} data to {output_path}")

