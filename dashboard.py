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

# --- تنسيق CSS المحدث (مع اعتماد اللون الأحمر الداكن الفاخر للثيم) ---
st.markdown("""
    <style>
    /* خلفية التطبيق الداكنة بالكامل */
    .stApp, header[data-testid="stHeader"] {
        background-color: #0d1117 !important;
    }
    
    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* العناوين والنصوص */
    h1, h2, h3, h4, span, label, p {
        color: #f0f6fc !important;
    }

    /* تنسيق التبويبات العلويّة المتجاوبة مع الجوال */
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
    /* اعتماد اللون الأحمر الداكن الفاخر للتبويب النشط */
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #7f1d1d 0%, #581c87 100%) !important;
        background-color: #7f1d1d !important;
        color: #ffffff !important;
        border: 1px solid #991b1b !important;
    }

    /* بطاقات الأداء المالي (لون مميز ومتناسق مع الأحمر الداكن) */
    [data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #fca5a5 !important;
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
            col3.metric("القوة الشرائية", f"${buying_power:,.2f}")
            
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
                        "سعر الدخول": f"${float(p.avg_entry_price):.2f}",
                        "السعر اللحظي": f"${float(p.current_price):.2f}",
                        "الربح/الخسارة ($)": f"${unrealized_pl:+.2f}",
                        "الربح/الخسارة (%)": f"{unrealized_plpc:+.2f}%"
                    })
                
                df_pos = pd.DataFrame(pos_list)
                st.dataframe(df_pos, use_container_width=True)
            else:
                st.info("لا توجد مراكز مفتوحة حالياً لهذا الحساب.")
                
            st.divider()
            
            st.subheader("📑 سجل العمليات والتنفيذ (CSV)")
            log_file = acc_data["LOG_FILE"]
            if os.path.exists(log_file):
                df_logs = pd.read_csv(log_file)
                st.dataframe(df_logs.tail(20), use_container_width=True)
            else:
                st.warning(f"لم يتم تسجيل صفقات في الملف {log_file} حتى الآن.")
                
        except Exception as e:
            st.error(f"خطأ في الاتصال: {e}")
    else:
        st.error("تعذر الاتصال بخوادم التداول.")

# --- التبويبات العلويّة ---
tabs = st.tabs([
    "🏛️ النظرة الشاملة",
    "🪙 الحساب الأول ($1000)",
    "💎 الحساب الثاني - bot2 ($2000)",
    "👑 الحساب الثاني - bot_account2 ($2000)"
])

# 1️⃣ الملخص الشامل
with tabs[0]:
    st.header("🏛️ الملخص المالي الموحد")
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
            "السيولة": f"${cash:,.2f}",
            "الصفقات المفتوحة": pos_count
        })
    
    st.metric("إجمالي المحافظ المدارة", f"${total_combined_equity:,.2f}")
    st.divider()
    
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True)

# 2️⃣ الحساب الأول
with tabs[1]:
    render_account_dashboard("الحساب الأول ($1000)", ACCOUNTS["الحساب الأول ($1000)"])

# 3️⃣ الحساب الثاني bot2
with tabs[2]:
    render_account_dashboard("الحساب الثاني - bot2 ($2000)", ACCOUNTS["الحساب الثاني - bot2 ($2000)"])

# 4️⃣ الحساب الثاني bot_account2
with tabs[3]:
    render_account_dashboard("الحساب الثاني - bot_account2 ($2000)", ACCOUNTS["الحساب الثاني - bot_account2 ($2000)"])

# --- التحديث اللحظي كل 10 ثوانٍ ---
time.sleep(10)
st.rerun()
