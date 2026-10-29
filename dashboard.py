import streamlit as st
import pandas as pd
import alpaca_trade_api as tradeapi
import os

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="Multi-Bot Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("🚀 لوحة التحكم المركزية للبوتات والحسابات")
st.markdown("متابعة حية لأداء الحسابات والصفقات النشطة والملفات التجارية.")

# --- تعريف بيانات الحسابات ومفاتيح الربط ---
ACCOUNTS = {
    "الحساب الأول (أسهم $1000)": {
        "API_KEY": "PKOEYQXJQFVILWXK6C4V5LXSXW",
        "SECRET_KEY": "A6zB4DC1idneqFUke5rEPp2hEAHYCDQCj8hjNmkS2zGf",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_account1.csv"
    },
    "الحساب الثاني (bot2 - $2000)": {
        "API_KEY": "PKGW26NSZJDLAMW2M7VSHJYMSL",
        "SECRET_KEY": "DpyM3KjPxBr4NumicNKVs7YczJuwZiudDMAxP84NCsTP",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_bot2.csv"
    },
    " 0.50 - 100 الحساب (bot_account2 - $2000)": {
        "API_KEY": "PKF5ARLBNCOULM3IMMSUZE4CIG",
        "SECRET_KEY": "CYdhvBVFGh6gKh3DAWJM7X8KgujxD7PjptCEa43MPc7k",
        "BASE_URL": "https://paper-api.alpaca.markets",
        "LOG_FILE": "trades_history_bot_account2.csv"
    }
}

# --- القائمة الجانبية للاختيار ---
st.sidebar.header("🎛️ لوحة التحكم")
selected_account_name = st.sidebar.selectbox(
    "اختر الحساب للعرض:",
    list(ACCOUNTS.keys()) + ["🌐 الملخص الشامل لجميع الحسابات"]
)

# دالة للاتصال بمنصة Alpaca لكل حساب بأمان
def get_alpaca_client(acc_config):
    try:
        return tradeapi.REST(
            acc_config["API_KEY"],
            acc_config["SECRET_KEY"],
            acc_config["BASE_URL"],
            api_version='v2'
        )
    except Exception as e:
        return None

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
            
            # بطاقات الملخص المالي
            col1, col2, col3 = st.columns(3)
            col1.metric("إجمالي المحفظة (Equity)", f"${equity:,.2f}")
            col2.metric("الكاش المتاح (Cash)", f"${cash:,.2f}")
            col3.metric("القوة الشرائية", f"${buying_power:,.2f}")
            
            st.divider()
            
            # جلب الصفقات المفتوحة
            st.subheader("📌 الصفقات النشطة حالياً")
            positions = api.list_positions()
            
            if positions:
                pos_list = []
                for p in positions:
                    pos_list.append({
                        "الرمز": p.symbol,
                        "الكمية": p.qty,
                        "سعر الدخول": f"${float(p.avg_entry_price):.2f}",
                        "السعر الحالي": f"${float(p.current_price):.2f}",
                        "الربح/الخسارة %": f"{float(p.unrealized_plpc)*100:+.2f}%",
                        "الربح/الخسارة $": f"${float(p.unrealized_pl):+.2f}"
                    })
                df_pos = pd.DataFrame(pos_list)
                st.dataframe(df_pos, use_container_width=True)
            else:
                st.info("لا توجد صفقات مفتوحة حالياً لهذا الحساب.")
                
            st.divider()
            
            # سجل الصفقات المحفوظ
            st.subheader("📜 سجل الصفقات التاريخي (CSV)")
            log_file = acc_data["LOG_FILE"]
            if os.path.exists(log_file):
                df_logs = pd.read_csv(log_file)
                st.dataframe(df_logs.tail(20), use_container_width=True)
            else:
                st.warning(f"لم يتم العثور على ملف السجل `{log_file}` بعد.")
                
        except Exception as e:
            st.error(f"حدث خطأ أثناء جلب بيانات الحساب من Alpaca: {e}")
    else:
        st.error("فشل الاتصال بمنصة التداول لهذا الحساب.")

# --- عرض الملخص الشامل لجميع الحسابات ---
else:
    st.header("🌐 نظرة عامة شاملة لكل الحسابات")
    
    total_combined_equity = 0.0
    summary_data = []
    
    for name, config in ACCOUNTS.items():
        api = get_alpaca_client(config)
        eq = 0.0
        cash = 0.0
        pos_count = 0
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
            "الكاش": f"${cash:,.2f}",
            "الصفقات النشطة": pos_count
        })
    
    st.metric("إجمالي رأس المال المدار بكل الحسابات", f"${total_combined_equity:,.2f}")
    st.divider()
    
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True)
