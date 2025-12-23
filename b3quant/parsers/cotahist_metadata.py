"""
COTAHIST file metadata and field specifications.

Reference:
    http://www.b3.com.br/data/files/C8/F3/08/B4/297BE410F816C9E492D828A8/SeriesHistoricas_Layout.pdf
"""

from enum import Enum

# Field widths for fixed-width format parsing
FIELD_WIDTHS = {
    "record_type": 2,
    "trade_date": 8,
    "bdi_code": 2,
    "ticker": 12,
    "market_type": 3,
    "company_name": 12,
    "specification": 10,
    "forward_days": 3,
    "currency": 4,
    "open_price": 13,
    "high_price": 13,
    "low_price": 13,
    "avg_price": 13,
    "close_price": 13,
    "best_bid": 13,
    "best_ask": 13,
    "trades_count": 5,
    "quantity": 18,
    "volume": 18,
    "strike_price": 13,
    "exercise_indicator": 1,
    "maturity_date": 8,
    "quote_factor": 7,
    "strike_price_points": 13,
    "isin": 12,
    "distribution": 3,
}

# Date columns (YYYYMMDD format)
DATE_COLUMNS = (
    "trade_date",
    "maturity_date",
)

# Price columns (stored as integers with 2 decimal places, need division by 100)
PRICE_COLUMNS = (
    "open_price",
    "high_price",
    "low_price",
    "avg_price",
    "close_price",
    "best_bid",
    "best_ask",
    "strike_price",
    "strike_price_points",
)

# Integer columns (no conversion needed)
INTEGER_COLUMNS = (
    "trades_count",
    "quantity",
    "volume",
    "quote_factor",
    "exercise_indicator",
    "distribution",
    "forward_days",
)

# String columns (strip whitespace)
STRING_COLUMNS = (
    "record_type",
    "bdi_code",
    "ticker",
    "market_type",
    "company_name",
    "specification",
    "currency",
    "isin",
)

# Market type code mappings
MARKET_TYPES = {
    "010": "STOCK",
    "012": "SUBSCRIPTION_RIGHTS",
    "013": "SUBSCRIPTION_RIGHTS_EXERCISE",
    "014": "SUBSCRIPTION_RECEIPTS",
    "017": "AUCTION",
    "020": "UNIT",
    "030": "BDR",
    "050": "ETF",
    "060": "TERM",
    "070": "CALL",
    "080": "PUT",
}


class InstrumentCategory(Enum):
    """Market type code groups for different instrument categories."""

    OPTION = ["070", "080"]  # CALL and PUT
    STOCK = "010"


# BDI code mappings
BDI_CODES = {
    "02": "STANDARD_LOT",
    "05": "SANCTIONED",
    "06": "CONCORDANCE",
    "07": "EXTRAJUDICIAL_RECOVERY",
    "08": "JUDICIAL_RECOVERY",
    "09": "SPECIAL_TEMPORARY_ADMINISTRATION",
    "10": "RIGHTS_AND_RECEIPTS",
    "11": "INTERVENTION",
    "12": "REAL_ESTATE_FUNDS",
    "14": "INVESTMENT_CERTS",
    "18": "OBLIGATIONS",
    "22": "PRIVATE_BONDS",
    "26": "PUBLIC_BONDS",
    "32": "INDEX_CALL_EXERCISE",
    "33": "INDEX_PUT_EXERCISE",
    "38": "STOCK_CALL_EXERCISE",
    "42": "STOCK_PUT_EXERCISE",
    "46": "UNLISTED_AUCTION",
    "48": "PRIVATIZATION_AUCTION",
    "50": "AUCTION",
    "56": "COURT_SALE",
    "58": "OTHERS",
    "60": "STOCK_EXCHANGE",
    "62": "TERM_MARKET",
    "70": "FUTURES_GAIN_RETENTION",
    "71": "FUTURES_MARKET",
    "74": "INDEX_CALL",
    "75": "INDEX_PUT",
    "78": "STOCK_CALL",
    "82": "STOCK_PUT",
    "96": "FRACTIONAL_MARKET",
}
