import requests
from decimal import Decimal
from django.conf import settings

def get_crypto_price(symbol):
    """获取加密货币价格"""
    try:
        # 使用 Binance API
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        response = requests.get(url)
        data = response.json()
        return Decimal(str(data['price']))
    except Exception as e:
        return None

def get_stock_price(symbol):
    """获取股票价格"""
    try:
        # 使用 Alpha Vantage API
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={settings.ALPHA_VANTAGE_API_KEY}"
        response = requests.get(url)
        data = response.json()
        return Decimal(str(data['Global Quote']['05. price']))
    except Exception as e:
        return None

def get_forex_price(symbol):
    """获取外汇价格"""
    try:
        # 使用 Alpha Vantage API
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={symbol[:3]}&to_currency={symbol[3:]}&apikey={settings.ALPHA_VANTAGE_API_KEY}"
        response = requests.get(url)
        data = response.json()
        return Decimal(str(data['Realtime Currency Exchange Rate']['5. Exchange Rate']))
    except Exception as e:
        return None

def get_commodity_price(symbol):
    """获取大宗商品价格"""
    try:
        # 使用 Alpha Vantage API
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={symbol}&to_currency=USD&apikey={settings.ALPHA_VANTAGE_API_KEY}"
        response = requests.get(url)
        data = response.json()
        return Decimal(str(data['Realtime Currency Exchange Rate']['5. Exchange Rate']))
    except Exception as e:
        return None 