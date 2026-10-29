import streamlit as st
import pandas as pd
import alpaca_trade_api as tradeapi
import time

# إعدادات الاتصال بـ Alpaca (نفس مفاتيح بوتك)
API_KEY = "PKOEYQXJQFVILWXK6C4V5LXSXW"
SECRET_KEY = "A6zB4DC1idneqFUke5rEPp2hEAHYCDQCj8hjNmkS2zGf"
BASE_URL = "https://paper-api.alpaca.markets"

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')

st.set_page_config(page_title="Trading Bot Dashboard", page_icon="📈", layout="wide")

# تصميم الواجهة الداكنة والمتناسقة مع الجوال
st.markdown("""
    <style>
    .main {background-color: #0e1117;}
    .metric-card {background-color: #1e2530; padding: 15px; border-radius: 10px; text-align: center;}
    </style>
""", unsafe_allow_html=True)

st.title("🚀 لوحة تحكم بوت التداول - الحساب الأول")
st.markdown("متابعة حية للأسهم، الأرباح، الصفقات النشطة، والأهداف.")

# جلب بيانات الحساب
try:
    account = api.get_account()
    equity = float(account.equity)
    cash = float(account.cash)
    buying_power = float(account.buying_power)
except Exception as e:
    st.error(f"خطأ في الاتصال بمنصة Alpaca: {e}")
    equity, cash, buying_power = 0, 0, 0

# بطاقات الملخص العلوي (Key Metrics)
col1, col2, col3, col4 = st.columns(4)
col1.metric("إجمالي المحفظة (Equity)", f"${equity:,.2f}")
col2.metric("الكاش المتاح (Cash)", f"${cash:,.2f}")
col3.metric("القوة الشرائية", f"${buying_power:,.2f}")

# جلب الصفقات المفتوحة حالياً من المنصة
try:
    positions = api.list_positions()
except Exception:
    positions = []

col4.metric("الصفقات النشطة", len(positions))

st.markdown("---")
st.subheader("📊 الصفقات المفتوحة حالياً (Active Trades)")

if not positions:
    st.info("لا توجد صفقات مفتوحة حالياً. البوت يبحث عن فرص جديدة...")
else:
    pos_data = []
    for p in positions:
        symbol = p.symbol
        qty = int(float(p.qty))
        avg_price = float(p.avg_entry_price)
        current_price = float(p.current_price)
        pnl_pct = float(p.unrealized_plpc) * 100
        pnl_usd = float(p.unrealized_pl)
        
        pos_data.append({
            "السهم": symbol,
            "الكمية": qty,
            "سعر الشراء": f"${avg_price:.2f}",
            "السعر الحالي": f"${current_price:.2f}",
            "الربح/الخسارة %": f"{pnl_pct:+.2f}%",
            "الربح/الخسارة $": f"${pnl_usd:+,.2f}"
        })
    
    df_pos = pd.DataFrame(pos_data)
    st.dataframe(df_pos, use_container_width=True)

# سجل الصفقات السابقة من ملف الـ CSV
st.markdown("---")
st.subheader("📜 سجل العمليات التاريخية (Trade Log History)")
try:
    if os.path.exists("trades_history_account1.csv"):
        df_log = pd.read_csv("trades_history_account1.csv")
        st.dataframe(df_log.tail(15), use_container_width=True)
    else:
        st.write("لا يوجد سجل عمليات حتى الآن.")
except Exception as e:
    st.write(f"تعذر قراءة سجل الصفقات: {e}")

# زر تحديث تلقائي للصفحة كل 10 ثوانٍ
if st.button("🔄 تحديث البيانات الآن"):
    st.rerun()