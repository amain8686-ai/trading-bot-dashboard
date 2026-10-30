import streamlit as st
import pandas as pd
import alpaca_trade_api as tradeapi
import os
import time

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="Live Multi-Bot Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("🚀 لوحة التحكم المباشرة للبوتات والحسابات")

# --- إضافة تحديث تلقائي حقيقي للأسعار كل 10 ثوانٍ ---
st.sidebar.header("🔄 التحديث اللحظي")
auto_refresh = st.sidebar.checkbox("تفعيل التحديث التلقائي المباشر", value=True)
refresh_interval = st.sidebar.slider("معدل التحديث (بالثواني):", min_value=3, max_value=60, value=10)

# --- تعريف بيانات الحسابات ومفاتيح الربط ---
ACCOUNTS = {
    "الحساب الأول (أسهم $1000)": {
        "API_KEY": "PKOEYQXJQFVILWXK6C4V5LXSXW",
        "SECRET_KEY": "A6zB4DC1idneqFUke5rEPp2hEAHYCDQCj8hjNmkS2zGf",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_account1.csv"
    },
    "الحساب الثاني (نسخة A - $2000)": {
        "API_KEY": "PKF5ARLBNCOULM3IMMSUZE4CIG",
        "SECRET_KEY": "CYdhvBVFGh6gKh3DAWJM7X8KgujxD7PjptCEa43MPc7k",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_account2.csv"
    },
    "الحساب الثاني (نسخة B - $2000)": {
        "API_KEY": "PKGW26NSZJDLAMW2M7VSHJYMSL",
        "SECRET_KEY": "DpyM3KjPxBr4NumicNKVs7YczJuwZiudDMAxP84NCsTP",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_bot2.csv"
    }
}

selected_account_name = st.sidebar.selectbox(
    "اختر الحساب للعرض:",
    list(ACCOUNTS.keys()) + ["🌐 الملخص الشامل لجميع الحسابات"]
)

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

# دالة لتلوين قيم الربح والخسارة في الجدول
def style_pnl(val):
    if isinstance(val, (int, float)):
        color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
        return f'color: {color}; font-weight: bold;'
    return ''

# --- عرض الحساب المنفرد ---
if selected_account_name != "🌐 الملخص الشامل لجميع الحسابات":
    acc_data = ACCOUNTS[selected_account_name]
    st.header(f"📊 تفاصيل: {selected_account_name}")
    
    api = get_alpaca_client(acc_data)
    
    if api:
        try:
            account_info = api.get_account()
            equity = float(account_info.equity)
            cash = float(account_info.cash)
            buying_power = float(account_info.buying_power)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("إجمالي المحفظة (Equity)", f"${equity:,.2f}")
            col2.metric("الكاش المتاح (Cash)", f"${cash:,.2f}")
            col3.metric("القوة الشرائية", f"${buying_power:,.2f}")
            
            st.divider()
            
            st.subheader("📌 الصفقات النشطة حالياً (تحديث مباشر)")
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
                
                # تطبيق الألوان (أخضر للربح، أحمر للخسارة)
                styled_df = df_pos.style.applymap(
                    style_pnl, subset=["الربح/الخسارة ($)", "الربح/الخسارة (%)"]
                ).format({
                    "سعر الدخول": "${:.2f}",
                    "السعر اللحظي": "${:.2f}",
                    "الربح/الخسارة ($)": "${:+.2f}",
                    "الربح/الخسارة (%)": "{:+.2f}%"
                })
                
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.info("لا توجد صفقات مفتوحة حالياً لهذا الحساب.")
                
            st.divider()
            
            st.subheader("📜 سجل الصفقات التاريخي (CSV)")
            log_file = acc_data["LOG_FILE"]
            if os.path.exists(log_file):
                df_logs = pd.read_csv(log_file)
                st.dataframe(df_logs.tail(20), use_container_width=True)
            else:
                st.warning(f"لم يتم العثور على ملف السجل `{log_file}` بعد.")
                
        except Exception as e:
            st.error(f"حدث خطأ أثناء جلب البيانات: {e}")

# --- عرض الملخص الشامل ---
else:
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

# آلية إعادة إنعاش الصفحة تلقائياً لتجديد الأسعار اللحظية
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
