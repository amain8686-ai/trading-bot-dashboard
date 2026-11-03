import streamlit as st
import pandas as pd
import alpaca_trade_api as tradeapi
import os
import time

# --- إعدادات الصفحة الأساسية ---
st.set_page_config(
    page_title="Terminal | Enterprise Trading",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- تنسيق CSS الثابت ---
st.markdown("""
    <style>
    .stApp, header[data-testid="stHeader"] {
        background-color: #0d1117 !important;
    }
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    h1, h2, h3, h4, span, label, p {
        color: #f0f6fc !important;
    }
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
        background: linear-gradient(135deg, #7f1d1d 0%, #581c87 100%) !important;
        background-color: #7f1d1d !important;
        color: #ffffff !important;
        border: 1px solid #991b1b !important;
    }
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

st.title("💰 منصة إدارة المحافظ الآلية")
st.caption("مركز التحكم والرقابة اللحظية على بوتات التداول")

# --- تعريف بيانات الحسابات ومفاتيح الربط ---
ACCOUNTS = {
    "الحساب الأول ($1000)": {
        "API_KEY": "PKL5ENZ2JPZ5M4JVN7JUNWJP52",
        "SECRET_KEY": "3QWnGzU2vHA9Q8tWSMemktbJwuviZT31WaMgNHQZc7SQ",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_bot1.csv"
    },
    "الحساب الثاني - bot2 ($2000)": {
        "API_KEY": "PK245YWODY3OJCL55MFTKKPQU7",
        "SECRET_KEY": "Fk8tgx7oVWbxr1eDDeZPWigC8WkembXsuim9AhSsBM7z",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_bot2.csv"
    },
    "الحساب الثاني - bot_account2 ($2000)": {
        "API_KEY": "PKKI27AVLWBEHLXKQNFBQEKR5Q",
        "SECRET_KEY": "CZYEZUZ6cNp1kAvUaHmjJZRDwqeQwb5Aama4iyBUGx82",
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

# دالة لتلوين أعمدة الأرباح والخسائر بالأخضر والأحمر
def color_pnl(val):
    if isinstance(val, (int, float)):
        if val > 0:
            return 'color: #10b981; font-weight: bold;'
        elif val < 0:
            return 'color: #ef4444; font-weight: bold;'
    return 'color: #c9d1d9;'

def render_account_dashboard(account_name, acc_data):
    api = get_alpaca_client(acc_data)
    if api:
        try:
            account_info = api.get_account()
            equity = float(account_info.equity)
            cash = float(account_info.cash)
            buying_power = float(account_info.buying_power)
            
            positions = api.list_positions()
            
            # حساب إجمالي الربح/الخسارة اللحظي من الصفقات النشطة
            total_unrealized_pl = 0.0
            if positions:
                for p in positions:
                    total_unrealized_pl += float(p.unrealized_pl)

            # عرض 4 أعمدة للمؤشرات (تمت إضافة مجموع الربح)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("إجمالي المحفظة", f"${equity:,.2f}")
            col2.metric("السيولة المتاحة", f"${cash:,.2f}")
            col3.metric("القوة الشرائية", f"${buying_power:,.2f}")
            
            # تلوين قيمة مجموع الربح أخضر أو أحمر بناءً على القيمة
            pl_color_prefix = "+" if total_unrealized_pl >= 0 else ""
            col4.metric("مجموع الربح/الخسارة", f"{pl_color_prefix}${total_unrealized_pl:,.2f}")
            
            st.divider()
            
            st.subheader("📈 المراكز والصفقات النشطة")
            
            if positions:
                pos_list = []
                for p in positions:
                    qty = int(float(p.qty))
                    entry_price = float(p.avg_entry_price)
                    total_cost = qty * entry_price  # مجموع الشراء
                    
                    unrealized_pl = float(p.unrealized_pl)
                    unrealized_plpc = float(p.unrealized_plpc) * 100
                    
                    pos_list.append({
                        "الرمز": p.symbol,
                        "الكمية": qty,
                        "سعر الدخول": entry_price,
                        "مجموع الشراء": total_cost,
                        "السعر اللحظي": float(p.current_price),
                        "الربح/الخسارة ($)": unrealized_pl,
                        "الربح/الخسارة (%)": unrealized_plpc
                    })
                
                df_pos = pd.DataFrame(pos_list)
                
                styled_df = df_pos.style.map(
                    color_pnl, subset=["الربح/الخسارة ($)", "الربح/الخسارة (%)"]
                ).format({
                    "سعر الدخول": "${:.2f}",
                    "مجموع الشراء": "${:,.2f}",
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
    total_combined_pl = 0.0
    summary_data = []
    
    for name, config in ACCOUNTS.items():
        api = get_alpaca_client(config)
        eq, cash, pos_count, acc_pl = 0.0, 0.0, 0, 0.0
        if api:
            try:
                acc = api.get_account()
                eq = float(acc.equity)
                cash = float(acc.cash)
                positions = api.list_positions()
                pos_count = len(positions)
                for p in positions:
                    acc_pl += float(p.unrealized_pl)
                total_combined_equity += eq
                total_combined_pl += acc_pl
            except:
                pass
        summary_data.append({
            "اسم الحساب": name,
            "إجمالي المحفظة": f"${eq:,.2f}",
            "السيولة": f"${cash:,.2f}",
            "مجموع الربح/الخسارة": f"${acc_pl:+,.2f}",
            "الصفقات المفتوحة": pos_count
        })
    
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("إجمالي المحافظ المدارة", f"${total_combined_equity:,.2f}")
    col_s2.metric("إجمالي الأرباح/الخسائر الموحدة", f"${total_combined_pl:+,.2f}")
    
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
