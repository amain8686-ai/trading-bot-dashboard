import streamlit as st
import pandas as pd
import alpaca_trade_api as tradeapi
import os
import time

# --- إعدادات الصفحة الأساسية ---
st.set_page_config(
    page_title="Institutional Trading Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تنسيق CSS احترافي يماثل منصات التداول المؤسسية ---
st.markdown("""
    <style>
    /* خلفية التطبيق العامة */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* تنسيق التبويبات العلويّة احترافي */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        justify-content: center;
        background-color: #161b22;
        padding: 8px;
        border-radius: 12px;
        border: 1px solid #30363d;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: #8b949e;
        font-weight: 600;
        font-size: 14px;
        border: none;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb !important;
        color: #ffffff !important;
        box-shadow: 0px 4px 12px rgba(31, 111, 235, 0.3);
    }
    
    /* تصميم بطاقات المؤشرات المالية */
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 700 !important;
        color: #f0f6fc !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 13px !important;
        color: #8b949e !important;
        font-weight: 500 !important;
    }
    
    /* فاصل إنسيابي */
    hr {
        border-color: #21262d !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ منصة التحكم بالتداول المباشر")
st.caption("نظام التداول الآلي | التغطية اللحظية للحسابات والمحافظ")

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
        color = '#00E676' if val > 0 else '#FF5252' if val < 0 else '#8b949e'
        return f'color: {color}; font-weight: bold;'
    return ''

def render_account_dashboard(account_name, acc_data):
    api = get_alpaca_client(acc_data)
    if api:
        try:
            account_info = api.get_account()
            equity = float(account_info.equity)
            cash = float(account_info.cash)
            buying_power = float(account_info.buying_power)
            
            # بطاقات الأداء المالي بالتنسيق المؤسسي
            col1, col2, col3 = st.columns(3)
            col1.metric("إجمالي المحفظة (Equity)", f"${equity:,.2f}")
            col2.metric("الكاش المتاح (Cash)", f"${cash:,.2f}")
            col3.metric("القوة الشرائية (Buying Power)", f"${buying_power:,.2f}")
            
            st.divider()
            
            st.subheader("📊 الصفقات المفتوحة اللحظية")
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
                
                # استخدام map بدلاً من applymap لتفادي الخطأ مع الإصدارات الجديدة
                styled_df = df_pos.style.map(
                    style_pnl, subset=["الربح/الخسارة ($)", "الربح/الخسارة (%)"]
                ).format({
                    "سعر الدخول": "${:.2f}",
                    "السعر اللحظي": "${:.2f}",
                    "الربح/الخسارة ($)": "${:+.2f}",
                    "الربح/الخسارة (%)": "{:+.2f}%"
                })
                
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.info("💡 لا توجد صفقات مفتوحة حالياً لهذا الحساب.")
                
            st.divider()
            
            st.subheader("📜 سجل الصفقات التاريخي (CSV)")
            log_file = acc_data["LOG_FILE"]
            if os.path.exists(log_file):
                df_logs = pd.read_csv(log_file)
                st.dataframe(df_logs.tail(20), use_container_width=True)
            else:
                st.warning(f"لم يتم تسجيل صفقات جديدة في السجل `{log_file}` حتى الآن.")
                
        except Exception as e:
            st.error(f"حدث خطأ أثناء الاتصال: {e}")
    else:
        st.error("فشل الاتصال بمنصة التداول لهذا الحساب.")

# --- إنشاء التبويبات العلويّة ---
tabs = st.tabs([
    "🌐 الملخص الشامل",
    "📊 الحساب الأول ($1000)",
    "📊 الحساب الثاني - bot2 ($2000)",
    "📊 الحساب الثاني - bot_account2 ($2000)"
])

# 1️⃣ تبويب الملخص الشامل
with tabs[0]:
    st.header("🌐 نظرة عامة شاملة لكل الحسابات")
    total_combined_equity = 0.0
    summary_data = []
    
    for name, config in ACCOUNTS.items():
        api = get_alpaca_client(config)
        eq, cash, pos_count = 0.0, 0.0, 0
        if api:
            try:
                acc = api.get_account()
                eq = float(acc.equity)
                cash = float(acc.cash)
                positions = api.list_positions()
                pos_count = len(positions)
                total_combined_equity += eq
            except:
                pass
        summary_data.append({
            "اسم الحساب": name,
            "إجمالي المحفظة": f"${eq:,.2f}",
            "الكاش المتاح": f"${cash:,.2f}",
            "الصفقات النشطة": pos_count
        })
    
    st.metric("إجمالي رأس المال المدار بكل الحسابات", f"${total_combined_equity:,.2f}")
    st.divider()
    
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True)

# 2️⃣ تبويب الحساب الأول
with tabs[1]:
    render_account_dashboard("الحساب الأول ($1000)", ACCOUNTS["الحساب الأول ($1000)"])

# 3️⃣ تبويب الحساب الثاني bot2
with tabs[2]:
    render_account_dashboard("الحساب الثاني - bot2 ($2000)", ACCOUNTS["الحساب الثاني - bot2 ($2000)"])

# 4️⃣ تبويب الحساب الثاني bot_account2
with tabs[3]:
    render_account_dashboard("الحساب الثاني - bot_account2 ($2000)", ACCOUNTS["الحساب الثاني - bot_account2 ($2000)"])

# --- التحديث اللحظي للأسعار كل 10 ثوانٍ ---
time.sleep(10)
st.rerun()
