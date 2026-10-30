import streamlit as st
import pandas as pd
import alpaca_trade_api as tradeapi
import os
import time

# --- إعدادات الصفحة الأساسية ---
st.set_page_config(
    page_title="Terminal | Enterprise Trading",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- إعادة تصميم الألوان والخلفية والرموز بالكامل (Cyber Gold Theme) ---
st.markdown("""
    <style>
    /* خلفية التطبيق - أسود فحم فاخر */
    .stApp {
        background-color: #08090c;
        color: #d1d5db;
    }
    
    /* رأس الصفحة والتطبيقات */
    h1 {
        color: #f3f4f6 !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    
    /* تصميم التبويبات باللون الذهبي الداكن والأزرق الرمادي */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        justify-content: center;
        background-color: #111318;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #1f242d;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        white-space: pre-wrap;
        background-color: #161a23;
        border-radius: 8px;
        color: #9ca3af;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid #28303e;
        transition: all 0.2s ease-in-out;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #d97706 0%, #b45309 100%) !important;
        color: #ffffff !important;
        border: 1px solid #f59e0b !important;
        box-shadow: 0px 2px 12px rgba(217, 119, 6, 0.35);
    }
    
    /* بطاقات الأداء المالي */
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #f59e0b !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 12px !important;
        color: #6b7280 !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
    }
    
    /* الفواصل */
    hr {
        border-color: #1f2937 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚜️ منصة إدارة المحافظ الآلية")
st.caption("مركز التحكم والرقابة اللحظية على بوتات التداول")

# --- تعريف بيانات الحسابات ومفاتيح الربط ---
ACCOUNTS = {
    "الحساب الأول ($1000)": {
        "API_KEY": "PKOEYQXJQFVILWXK6C4V5LXSXW",
        "SECRET_KEY": "A6zB4DC1idneqFUke5rEPp2hEAHYCDQCj8hjNmkS2zGf",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_bot1.csv"
    },
    "الحساب الثاني - bot2 ($2000)": {
        "API_KEY": "PKGW26NSZJDLAMW2M7VSHJYMSL",
        "SECRET_KEY": "DpyM3KjPxBr4NumicNKVs7YczJuwZiudDMAxP84NCsTP",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_bot2.csv"
    },
    "الحساب الثاني - bot_account2 ($2000)": {
        "API_KEY": "PKF5ARLBNCOULM3IMMSUZE4CIG",
        "SECRET_KEY": "CYdhvBVFGh6gKh3DAWJM7X8KgujxD7PjptCEa43MPc7k",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_account2.csv"
    }
}

def get_alpaca_client(acc_config):
    try:
        return tradeapi.REST(
            acc_config["API_KEY"],
            acc_config["SECRET_KEY"],
            acc_config["BASE_URL"],
            api_version='v2'
        )
    except Exception:
        return None

def style_pnl(val):
    if isinstance(val, (int, float)):
        color = '#10b981' if val > 0 else '#f43f5e' if val < 0 else '#6b7280'
        return f'color: {color}; font-weight: bold;'
    return ''

def render_account_dashboard(account_name, acc_data):
    api = get_alpaca_client(acc_data)
    if api:
        try:
            account_info = api.get_account()
