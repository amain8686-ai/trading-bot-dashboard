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

# --- التنسيق البصري (Cyber Gold Theme) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #08090c;
        color: #d1d5db;
    }
    
    h1 {
        color: #f3f4f6 !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    
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

def style_pnl_column(s):
    colors = []
    for val in s:
        if isinstance(val, (int, float)):
            if val > 0:
                colors.append('color: #10b981; font-weight: bold;')
            elif val < 0:
                colors.append('color: #f43f5e; font-weight: bold;')
            else:
                colors.append('color: #6b7280;')
        else:
            colors.append('')
    return colors

def render_account_dashboard(account_name, acc_data):
    api = get_alpaca_client(acc_data)
    if api:
        try:
            account_info = api.get_account()
            equity = float(account_info.equity)
            cash = float(account_info.cash)
            buying_power = float(account_info.buying_power)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("إجمالي المحفظة (Equity)", f"${equity:,.2f}")
            col2.metric("السيولة المتاحة (Cash)", f"${cash:,.2f}")
            col3.metric("القوة الشرائية (Buying Power)", f"${buying_power:,.2f}")
            
            st.divider()
            
            st.subheader("📈 المراكز والصفقات النشطة")
            positions = api.list_positions()
            
            if positions:
                pos_list = []
                for p in positions:
                    unrealized_pl = float(p.unrealized_pl)
                    unrealized_plpc = float(p.unrealized_plpc) * 100
                    
                    pos_list.append({
                        "الرمز": p.symbol,
                        "الكمية": int(float(p.qty)),
                        "سعر الدخول": float(p.avg_entry_price),
                        "السعر اللحظي": float(p.current_price),
                        "الربح/الخسارة ($)": unrealized_pl,
                        "الربح/الخسارة (%)": unrealized_plpc
                    })
                
                df_pos = pd.DataFrame(pos_list)
                
                # تم التعديل هنا لتفادي أي خطأ في إصدارات Pandas المحدثة
                styled_df = df_pos.style.apply(
                    style_pnl_column, subset=["الربح/الخسارة ($)", "الربح/الخسارة (%)"]
                ).format({
                    "سعر الدخول": "${:.2f}",
                    "السعر اللحظي": "${:.2f}",
                    "الربح/الخسارة ($)": "${:+.2f}",
                    "الربح/الخسارة (%)": "{:+.2f}%"
                })
                
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.info("لا توجد مراكز مفتوحة حالياً لهذا الحساب.")
                
            st.divider()
            
            st.subheader("📑 سجل العمليات والتنفيذ (CSV)")
            log_file = acc_data["LOG_FILE"]
            if os.path.exists(log_file):
                df_logs = pd.read_csv(log_file)
                st.dataframe(df_logs.tail(20), use_container_width=True)
            else:
                st.warning(f"لم يتم
