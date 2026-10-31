import streamlit as st
import pandas as pd
import alpaca_trade_api as tradeapi
import os
import time

# --- إعدادات الصفحة أساسية وتحديد الثيم الداكن رسمياً ---
st.set_page_config(
    page_title="Terminal | Enterprise Trading",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تنسيق CSS مخصص للواجهة بدون تحريب ألوان الجداول ---
st.markdown("""
    <style>
    /* 1. صبغ خلفية التطبيق بالكامل باللون الأسود وتغطية الشريط العلوي */
    .stApp, header[data-testid="stHeader"] {
        background-color: #0d1117 !important;
    }
    
    /* 2. إخفاء الهيدر الشفاف الأبيض العلوي الخاص بـ Streamlit */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* 3. تنسيق العناوين والنصوص الرئيسية */
    h1, h2, h3, h4, span, label, p {
        color: #f0f6fc !important;
    }

    /* 4. تنسيق التبويبات العلويّة */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        justify-content: center;
        background-color: #161b22 !important;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #30363d !important;
        flex-wrap: wrap !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: auto !important;
        min-height: 40px;
        background-color: #21262d !important;
        border-radius: 8px;
        color: #c9d1d9 !important;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid #30363d !important;
        padding: 8px 16px !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #d97706 0%, #b45309 100%) !important;
        color: #ffffff !important;
        border: 1px solid #f59e0b !important;
    }

    /* 5. بطاقات الأداء المالي */
    [data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #f59e0b !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 12px !important;
        color: #8b949e !important;
        font-weight: 600 !important;
    }

    hr {
        border-color: #30363d !important;
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

def render_account_dashboard(account_name, acc_data):
    api = get_alpaca_client(acc_data)
    if api:
        try:
            account_info = api.get_account()
            equity = float(account_info.equity)
            cash = float(account_info.cash)
            buying_power = float(account_info.buying_power)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("إجمالي المحفظة", f"${equity:,.2f}")
            col2.metric("السيولة المتاحة", f"${cash:,.2f}")
            col3.
