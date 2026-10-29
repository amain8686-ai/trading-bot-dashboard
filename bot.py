import time
import datetime
import os
import csv
import random
import requests
import warnings
import json
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import alpaca_trade_api as tradeapi
import os
os.environ['CURL_CA_BUNDLE'] = ''

warnings.filterwarnings("ignore")

# --- Alpaca Paper Trading API Credentials (الحساب الأول الأصلي - $1000) ---
API_KEY = "PKOEYQXJQFVILWXK6C4V5LXSXW"
SECRET_KEY = "A6zB4DC1idneqFUke5rEPp2hEAHYCDQCj8hjNmkS2zGf"
BASE_URL = "https://paper-api.alpaca.markets"

# --- Telegram Settings ---
TELEGRAM_BOT_TOKEN = "8971971904:AAFkbxmFC80qzO1NvGiFw8EU2n-pFV8K3Ww"
TELEGRAM_CHAT_ID = "1799920145"

# --- Gemini API Key (أدخلي مفتاح الذكاء الاصطناعي هنا) ---
GEMINI_API_KEY = "AQ.Ab8RN6KE_7c3PvSOLRc7fZ1xfEhL4ULz_AjoSYi0N001jksl8w"

# --- Risk Management Constants ---
MAX_DAILY_LOSS_PCT = 0.02

# --- إعدادات رأس المال والصفقات للحساب الأول ---
MAX_ACTIVE_POSITIONS = 2       # الحد الأقصى الصارم: صفقتان فقط
CAPITAL_ALLOCATION_PCT = 0.45  # تخصيص 45% من إجمالي الحساب لكل صفقة

# --- إعدادات وقف الخسارة وجني الأرباح المحدثة ---
SOFT_STOP_LOSS_PCT = 0.015          # 1.5% خسارة تبدأ مهلة 10 دقائق
HARD_STOP_LOSS_PCT = 0.020          # 2.0% خسارة بيع فوري بدون انتظار
SOFT_STOP_BUFFER_SECONDS = 600       # 10 دقائق مهلة وقف الخسارة

SOFT_TRAILING_DROP_PCT = 0.015      # 1.5% تراجع من القمة تبدأ مهلة 5 دقائق
HARD_TRAILING_DROP_PCT = 0.020      # 2.0% تراجع من القمة بيع فوري بدون انتظار
SOFT_TRAILING_BUFFER_SECONDS = 300  # 5 دقائق مهلة للتراجع من القمة

# --- النطاق السعري للحساب الأول ---
MIN_STOCK_PRICE = 10.0
MAX_STOCK_PRICE = 200.0

TRADE_LOG_FILE = "trades_history_account1.csv"

def init_trade_log():
    if not os.path.exists(TRADE_LOG_FILE):
        try:
            with open(TRADE_LOG_FILE, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Symbol", "Exchange", "Action", "Qty", "Price", "Details"])
        except Exception as e:
            print(f"[!] Error creating trade log file: {e}")

def log_trade_to_csv(symbol, exchange, action, qty, price, details=""):
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(TRADE_LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, symbol, exchange, action, qty, price, details])
    except Exception as e:
        print(f"[!] Error writing to trade log: {e}")

init_trade_log()

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')

NON_COMPLIANT_SYMBOLS = {
    "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "BLK", "SCHW", "PFE", 
    "PM", "MO", "BUD", "DEO", "LVS", "WYNN", "MGM", "CZR", "DIS"
}

starting_equity = None
trading_halted_today = False
current_date_str = ""

compliance_cache = {}
rvol_cache = {}
peak_prices = {}
soft_stop_timers = {}
soft_trailing_timers = {}
stock_exchanges = {}

sold_cooldown_registry = {}
COOLDOWN_HOURS = 24 

def send_telegram(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID and "YOUR_TELEGRAM" not in TELEGRAM_BOT_TOKEN:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
        except Exception as e:
            print(f"[!] Telegram Error: {e}")

# ==================== طبقة الذكاء الاصطناعي والتحليل الإخباري والأهداف ====================
def analyze_with_ai(symbol, current_price, news_list):
    """
    استخدام Gemini للتحقق من الأخبار وتوليد الأهداف المتعددة (TP1, TP2, TP3)
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return True, "No AI Key Provided", round(current_price * 1.015, 2), round(current_price * 1.03, 2), round(current_price * 1.05, 2)

    prompt = f"""
    Analyze stock {symbol} currently priced at ${current_price}.
    Recent news titles: {news_list[:3]}
    Tasks:
    1. Determine sentiment: POSITIVE, NEUTRAL, or NEGATIVE.
    2. Provide 3 dynamic target prices (TP1 ~1.5%, TP2 ~3%, TP3 ~5%).
    Respond ONLY in this JSON format:
    {{"sentiment": "POSITIVE", "tp1": 0.0, "tp2": 0.0, "tp3": 0.0, "reason": "brief reason"}}
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload, timeout=8).json()
        
        text_resp = res['candidates'][0]['content']['parts'][0]['text']
        clean_json = text_resp.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        is_safe = data.get("sentiment") != "NEGATIVE"
        return is_safe, data.get("reason", "AI Approved"), float(data.get("tp1", current_price * 1.015)), float(data.get("tp2", current_price * 1.03)), float(data.get("tp3", current_price * 1.05))
    except Exception as e:
        print(f"⚠️ AI Analysis bypassed due to error: {e}")
        return True, "AI Error Bypassed", round(current_price * 1.015, 2), round(current_price * 1.03, 2), round(current_price * 1.05, 2)

def is_regular_market_open():
    try:
        clock = api.get_clock()
        return clock.is_open
    except Exception:
        return True

def is_market_bullish():
    try:
        spy_df = yf.download("SPY", period="30d", interval="1d", progress=False, auto_adjust=True, timeout=10)
        if spy_df.empty or len(spy_df) < 20:
            return True 
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)
        
        spy_df['SMA_20'] = ta.sma(spy_df['Close'], length=20)
        last_close = float(spy_df['Close'].iloc[-1])
        last_sma20 = float(spy_df['SMA_20'].iloc[-1])
        
        return last_close >= (last_sma20 * 0.99)
    except Exception:
        return True

def get_dynamic_universe():
    global stock_exchanges
    try:
        assets = api.list_assets(status='active', asset_class='us_equity')
        symbols = []
        stock_exchanges.clear()
        for asset in assets:
            if asset.tradable and asset.exchange in ['NASDAQ', 'NYSE']:
                sym = asset.symbol
                if '.' not in sym and '-' not in sym and len(sym) <= 5:
                    symbols.append(sym)
                    stock_exchanges[sym] = asset.exchange
        
        random.shuffle(symbols)
        selected_symbols = symbols[:400]
        print(f"✅ Scanning {len(selected_symbols)} NASDAQ & NYSE stocks ($10 - $200)...")
        return selected_symbols
    except Exception as e:
        print(f"⚠️ Error fetching universe: {e}")
        return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA", "AMD", "META", "JNJ", "UNH"]

def is_sharia_compliant(symbol):
    global compliance_cache
    today = datetime.datetime.now().date()
    if symbol in NON_COMPLIANT_SYMBOLS:
        return False
    if symbol in compliance_cache:
        return compliance_cache[symbol][1]

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        sector = info.get('sector', '')
        industry = info.get('industry', '')
        if sector in ['Financial Services', 'Banking'] or any(ind in industry for ind in ['Gambling', 'Tobacco', 'Alcoholic Beverages']):
            compliance_cache[symbol] = (today, False)
            return False
        if (info.get('totalDebt', 0) / info.get('marketCap', 1)) > 0.33:
            compliance_cache[symbol] = (today, False)
            return False
        compliance_cache[symbol] = (today, True)
        return True
    except Exception:
        return symbol not in NON_COMPLIANT_SYMBOLS

def check_rvol(symbol, threshold=0.95):
    global rvol_cache
    today = datetime.datetime.now().date()
    if symbol in rvol_cache:
        return rvol_cache[symbol][2], rvol_cache[symbol][1]

    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="3mo", interval="1d", auto_adjust=True)
        if len(df) < 60:
            return False, 1.0
            
        avg_volume_20 = df['Volume'].iloc[-16:-1].mean()
        latest_volume = df['Volume'].iloc[-1]
        rvol = latest_volume / avg_volume_20 if avg_volume_20 > 0 else 1.0
        passed = rvol >= threshold
        rvol_cache[symbol] = (today, rvol, passed)
        return passed, rvol
    except Exception:
        return False, 1.0

def check_weekly_trend(symbol):
    try:
        df_weekly = yf.download(symbol, period="6mo", interval="1wk", progress=False, auto_adjust=True, timeout=10)
        if df_weekly.empty or len(df_weekly) < 20:
            return True
        if isinstance(df_weekly.columns, pd.MultiIndex):
            df_weekly.columns = df_weekly.columns.get_level_values(0)
            
        df_weekly['SMA_20'] = ta.sma(df_weekly['Close'], length=20)
        last_close = float(df_weekly['Close'].iloc[-1])
        last_sma20 = float(df_weekly['SMA_20'].iloc[-1])
        
        return last_close >= last_sma20
    except Exception:
        return True

def advanced_metrics_analysis(symbol, latest_price):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        market_cap = info.get('marketCap', 0)
        if not market_cap or market_cap < 10_000_000:
            return False

        volume = info.get('volume', 0)
        if not volume or volume < 50_000:
            return False

        return True
    except Exception:
        return True

def check_daily_risk_limits():
    global starting_equity, trading_halted_today, current_date_str
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    if today_str != current_date_str:
        current_date_str = today_str
        trading_halted_today = False
        try:
            account = api.get_account()
            starting_equity = float(account.equity)
            send_telegram(f"🌅 **Account 1 New Trading Day ({today_str})**\nStarting Equity: `${starting_equity:.2f}`")
        except Exception:
            return False

    if trading_halted_today:
        return False

    try:
        account = api.get_account()
        current_equity = float(account.equity)
        if starting_equity and starting_equity > 0:
            if (current_equity - starting_equity) / starting_equity <= -MAX_DAILY_LOSS_PCT:
                trading_halted_today = True
                send_telegram(f"🛑 **Account 1 Daily Circuit Breaker Triggered!**")
                return False
    except Exception:
        pass
    return True

def send_hourly_positions_report():
    global stock_exchanges
    try:
        positions = api.list_positions()
        if not positions:
            send_telegram("📊 **Account 1 Hourly Update:** No active positions.")
            return

        report_lines = ["📊 **Account 1 Hourly Portfolio Update:**\n"]
        for pos in positions:
            symbol = pos.symbol
            exchange = stock_exchanges.get(symbol, "US")
            qty = int(float(pos.qty))
            profit_pct = float(pos.unrealized_plpc) * 100
            current_price = float(pos.current_price)
            avg_entry_price = float(pos.avg_entry_price)
            status_str = "PROFIT 🟢" if profit_pct >= 0 else "LOSS 🔴"
            report_lines.append(f"• `{symbol}` ({exchange}) | Qty: `{qty}` | Entry: `${avg_entry_price:.2f}` | PnL: `{profit_pct:+.2f}%` {status_str}")
        send_telegram("\n".join(report_lines))
    except Exception as e:
        print(f"❌ Error in hourly report: {e}")

def cancel_existing_orders_for_symbol(symbol):
    try:
        orders = api.list_orders(status='open', symbols=[symbol])
        for order in orders:
            api.cancel_order(order.id)
            time.sleep(0.5)
    except Exception as e:
        print(f"⚠️ Error canceling open orders for {symbol}: {e}")

def monitor_and_manage_positions():
    global peak_prices, sold_cooldown_registry, soft_stop_timers, soft_trailing_timers, stock_exchanges
    
    if not is_regular_market_open():
        return

    try:
        positions = api.list_positions()
        current_time_sec = time.time()

        for pos in positions:
            symbol = pos.symbol
            exchange = stock_exchanges.get(symbol, "US")
            qty = int(float(pos.qty))
            current_price = float(pos.current_price)
            avg_entry_price = float(pos.avg_entry_price)
            
            pnl_pct = (current_price - avg_entry_price) / avg_entry_price
            
            if pnl_pct <= -HARD_STOP_LOSS_PCT:
                cancel_existing_orders_for_symbol(symbol)
                api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='day')
                log_trade_to_csv(symbol, exchange, "HARD_STOP_LOSS_2PCT", qty, current_price, f"Hard Loss reached {pnl_pct*100:.2f}%")
                send_telegram(f"🚨 **Account 1 HARD STOP LOSS EXECUTED (2%)!**\nSymbol: `{symbol}` ({exchange})\nPrice: `${current_price:.2f}`\nLoss: `{pnl_pct*100:.2f}%`")
                
                sold_cooldown_registry[symbol] = datetime.datetime.now()
                if symbol in peak_prices: del peak_prices[symbol]
                if symbol in soft_stop_timers: del soft_stop_timers[symbol]
                if symbol in soft_trailing_timers: del soft_trailing_timers[symbol]
                continue

            if pnl_pct <= -SOFT_STOP_LOSS_PCT:
                if symbol not in soft_stop_timers:
                    soft_stop_timers[symbol] = current_time_sec
                else:
                    elapsed = current_time_sec - soft_stop_timers[symbol]
                    if elapsed >= SOFT_STOP_BUFFER_SECONDS:
                        cancel_existing_orders_for_symbol(symbol)
                        api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='day')
                        log_trade_to_csv(symbol, exchange, "SOFT_STOP_LOSS_10MIN", qty, current_price, f"Soft Loss persistent after 10 mins: {pnl_pct*100:.2f}%")
                        send_telegram(f"🛑 **Account 1 SOFT STOP LOSS EXECUTED (10 Mins Ended)!**\nSymbol: `{symbol}` ({exchange})\nPrice: `${current_price:.2f}`\nLoss: `{pnl_pct*100:.2f}%`")
                        
                        sold_cooldown_registry[symbol] = datetime.datetime.now()
                        if symbol in peak_prices: del peak_prices[symbol]
                        if symbol in soft_stop_timers: del soft_stop_timers[symbol]
                        if symbol in soft_trailing_timers: del soft_trailing_timers[symbol]
                        continue
            else:
                if symbol in soft_stop_timers:
                    del soft_stop_timers[symbol]

            if symbol not in peak_prices:
                peak_prices[symbol] = avg_entry_price
            
            if current_price > peak_prices[symbol]:
                peak_prices[symbol] = current_price
                if symbol in soft_trailing_timers:
                    del soft_trailing_timers[symbol]
            
            peak_price = peak_prices[symbol]
            if peak_price > avg_entry_price:
                drop_from_peak = (peak_price - current_price) / peak_price
                
                if drop_from_peak >= HARD_TRAILING_DROP_PCT:
                    cancel_existing_orders_for_symbol(symbol)
                    api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='day')
                    log_trade_to_csv(symbol, exchange, "HARD_TRAILING_TAKE_PROFIT", qty, current_price, f"Hard drop from peak {drop_from_peak*100:.2f}%")
                    send_telegram(f"🎯 **Account 1 HARD TRAILING TAKE PROFIT (2%)!**\nSymbol: `{symbol}` ({exchange})\nPeak: `${peak_price:.2f}`\nSell Price: `${current_price:.2f}`")
                    
                    sold_cooldown_registry[symbol] = datetime.datetime.now()
                    if symbol in peak_prices: del peak_prices[symbol]
                    if symbol in soft_stop_timers: del soft_stop_timers[symbol]
                    if symbol in soft_trailing_timers: del soft_trailing_timers[symbol]
                    continue

                if drop_from_peak >= SOFT_TRAILING_DROP_PCT:
                    if symbol not in soft_trailing_timers:
                        soft_trailing_timers[symbol] = current_time_sec
                    else:
                        elapsed = current_time_sec - soft_trailing_timers[symbol]
                        if elapsed >= SOFT_TRAILING_BUFFER_SECONDS:
                            cancel_existing_orders_for_symbol(symbol)
                            api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='day')
                            log_trade_to_csv(symbol, exchange, "SOFT_TRAILING_TAKE_PROFIT", qty, current_price, f"Soft drop persistent after 5 mins: {drop_from_peak*100:.2f}%")
                            send_telegram(f"🎯 **Account 1 SOFT TRAILING TAKE PROFIT (5 Mins Ended)!**\nSymbol: `{symbol}` ({exchange})\nPeak: `${peak_price:.2f}`\nSell Price: `${current_price:.2f}`")
                            
                            sold_cooldown_registry[symbol] = datetime.datetime.now()
                            if symbol in peak_prices: del peak_prices[symbol]
                            if symbol in soft_stop_timers: del soft_stop_timers[symbol]
                            if symbol in soft_trailing_timers: del soft_trailing_timers[symbol]
                            continue
                else:
                    if symbol in soft_trailing_timers:
                        del soft_trailing_timers[symbol]
    except Exception as e:
        print(f"⚠️ Error managing positions: {e}")

def scan_and_rank_market():
    print("🔍 Scanning candidates ($10 - $200 Range)...")
    candidates = []
    universe = get_dynamic_universe()
    now = datetime.datetime.now()
    
    for symbol in universe:
        if symbol in sold_cooldown_registry:
            elapsed_hours = (now - sold_cooldown_registry[symbol]).total_seconds() / 3600
            if elapsed_hours < COOLDOWN_HOURS:
                continue
            else:
                del sold_cooldown_registry[symbol]

        if not is_sharia_compliant(symbol):
            continue

        passed_rvol, rvol_val = check_rvol(symbol, threshold=0.95)
        if not passed_rvol:
            continue

        if not check_weekly_trend(symbol):
            continue

        try:
            df_15m = yf.download(symbol, period="5d", interval="15m", progress=False, auto_adjust=True, timeout=10)
            if df_15m.empty or len(df_15m) < 15:
                continue
            if isinstance(df_15m.columns, pd.MultiIndex):
                df_15m.columns = df_15m.columns.get_level_values(0)

            latest_price = float(df_15m['Close'].iloc[-1])
            
            if not (MIN_STOCK_PRICE <= latest_price <= MAX_STOCK_PRICE):
                continue

            if not advanced_metrics_analysis(symbol, latest_price):
                continue

            rsi_15m = float(ta.rsi(df_15m['Close'], length=14).iloc[-1])
            if not (30 <= rsi_15m <= 70):
                continue

            score = rvol_val + (rsi_15m / 10)
            candidates.append({'symbol': symbol, 'score': score, 'price': latest_price})
        except Exception:
            continue

    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates

def execute_ranked_trades():
    global stock_exchanges
    if trading_halted_today:
        return

    try:
        positions = api.list_positions()
        open_orders = api.list_orders(status='open')
        current_active_count = len(positions) + len(open_orders)
    except Exception:
        current_active_count = MAX_ACTIVE_POSITIONS

    slots_available = MAX_ACTIVE_POSITIONS - current_active_count
    if slots_available <= 0:
        return

    market_is_bull = is_market_bullish()
    required_rvol = 0.95 if market_is_bull else 2.0

    active_symbols = [p.symbol for p in positions] + [o.symbol for o in open_orders]
    ranked_list = scan_and_rank_market()

    executed_count = 0
    for item in ranked_list:
        if executed_count >= slots_available:
            break
        
        symbol = item['symbol']
        if symbol in active_symbols:
            continue

        try:
            passed_rvol, rvol_val = check_rvol(symbol, threshold=required_rvol)
            if not passed_rvol:
                continue

            ticker = yf.Ticker(symbol)
            news_items = ticker.news if hasattr(ticker, 'news') else []
            news_titles = [n.get('title', '') for n in news_items]

            latest_price = item['price']
            
            # فحص الذكاء الاصطناعي للأخبار وتوليد الأهداف الديناميكية
            is_safe, reason, tp1, tp2, tp3 = analyze_with_ai(symbol, latest_price, news_titles)
            if not is_safe:
                print(f"⛔ AI rejected {symbol}: {reason}")
                continue

            df_1h = yf.download(symbol, period="20d", interval="1h", progress=False, auto_adjust=True, timeout=10)
            if df_1h.empty or len(df_1h) < 15:
                continue
            if isinstance(df_1h.columns, pd.MultiIndex):
                df_1h.columns = df_1h.columns.get_level_values(0)

            df_1h['VWAP'] = ta.vwap(df_1h['High'], df_1h['Low'], df_1h['Close'], df_1h['Volume'])
            current_close = float(df_1h['Close'].iloc[-1])
            current_vwap = float(df_1h['VWAP'].iloc[-1]) if 'VWAP' in df_1h and not pd.isna(df_1h['VWAP'].iloc[-1]) else current_close
            
            df_1h['Vol_SMA'] = ta.sma(df_1h['Volume'], length=10)
            current_vol = float(df_1h['Volume'].iloc[-1])
            avg_vol = float(df_1h['Vol_SMA'].iloc[-1]) if 'Vol_SMA' in df_1h and not pd.isna(df_1h['Vol_SMA'].iloc[-1]) else current_vol

            rsi_1h = ta.rsi(df_1h['Close'], length=14).iloc[-1]
            macd_1h = df_1h.ta.macd(fast=12, slow=26, signal=9)
            
            if current_close >= current_vwap and current_vol >= (avg_vol * 0.85) and rsi_1h < 70 and macd_1h.iloc[:, 1].iloc[-1] > 0:
                exchange = stock_exchanges.get(symbol, "US")
                
                if not (MIN_STOCK_PRICE <= latest_price <= MAX_STOCK_PRICE):
                    continue

                account = api.get_account()
                total_equity = float(account.equity)
                free_cash = float(account.cash)
                target_budget = total_equity * CAPITAL_ALLOCATION_PCT
                
                min_cash_reserve = total_equity * 0.10
                if free_cash - target_budget < min_cash_reserve:
                    print(f"⚠️ Skipped {symbol}: Reserve limit reached.")
                    continue

                qty = int(target_budget // latest_price)
                if qty <= 0: qty = 1

                api.submit_order(symbol=symbol, qty=qty, side='buy', type='market', time_in_force='gtc')

                log_trade_to_csv(symbol, exchange, "BUY", qty, latest_price, f"Score: {item['score']:.2f} | AI: {reason}")
                
                # رسالة تليجرام مدعومة بالأهداف الذكية
                msg = (
                    f"🚀 **Account 1 BUY!**\n"
                    f"Symbol: `{symbol}` ({exchange})\n"
                    f"Shares: `{qty}` | Price: `${latest_price:.2f}`\n"
                    f"🧠 AI Sentiment: `{reason}`\n"
                    f"🎯 **AI Multi-Targets:**\n"
                    f"  - TP1: `${tp1}`\n"
                    f"  - TP2: `${tp2}`\n"
                    f"  - TP3: `${tp3}`"
                )
                send_telegram(msg)
                
                active_symbols.append(symbol)
                executed_count += 1
        except Exception as e:
            print(f"❌ Error executing trade for {symbol}: {e}")

print("🤖 Bot 1 Bot (Strict Position Limit Guard + AI Advisory & Weekly Trend | Running)...")
last_buy_scan_time = 0
last_hourly_report_time = 0

while True:
    try:
        if is_regular_market_open():
            current_time = time.time()
            if check_daily_risk_limits():
                
                monitor_and_manage_positions()

                if current_time - last_hourly_report_time >= 3600:
                    send_hourly_positions_report()
                    last_hourly_report_time = current_time

                try:
                    positions_check = api.list_positions()
                    orders_check = api.list_orders(status='open')
                    current_positions_count = len(positions_check) + len(orders_check)
                except Exception:
                    current_positions_count = MAX_ACTIVE_POSITIONS

                if current_positions_count < MAX_ACTIVE_POSITIONS and (current_time - last_buy_scan_time >= 45):
                    execute_ranked_trades()
                    last_buy_scan_time = current_time
                elif current_time - last_buy_scan_time >= 600:
                    execute_ranked_trades()
                    last_buy_scan_time = current_time
        else:
            time.sleep(60)
            continue

        time.sleep(10)
        
    except Exception as e:
        print(f"⚠️ Network or Connection Warning: {e}. Reconnecting in 30 seconds...")
        time.sleep(30)