import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="GABDO OTC INTELLIGENCE",page_icon="📡",layout="wide")
st.markdown("<style>.stApp{background:#080d18;color:#e8eefc}.block-container{padding-top:1.3rem}[data-testid=stMetric]{background:#111b2d;padding:14px;border-radius:12px}</style>",unsafe_allow_html=True)
st.title("📡 GABDO OTC INTELLIGENCE")
st.caption("Strategy-based OTC scanner • CALL / PUT / WAIT • Optional Telegram alerts")
PAIRS=["EUR/USD OTC","GBP/USD OTC","USD/JPY OTC","AUD/USD OTC","EUR/GBP OTC","USD/CAD OTC","NZD/USD OTC","GBP/JPY OTC"]
FRAMES=["5 seconds","15 seconds","30 seconds","1 minute","5 minutes"]
with st.sidebar:
    st.header("Scanner settings")
    pair=st.selectbox("OTC pair",PAIRS)
    timeframe=st.selectbox("Timeframe",FRAMES,index=2)
    mode=st.radio("Data source",["Upload candle CSV","Demo mode"])
    threshold=st.slider("Minimum signal score",50,95,70,5)
    st.divider()
    st.subheader("Telegram alerts")
    token=st.text_input("Bot token",type="password")
    chat=st.text_input("Chat ID")
    test=st.button("Send test alert")

def make_demo(n=260):
    rng=np.random.default_rng()
    close=rng.normal(0,0.00045,n).cumsum()+1.08
    op=np.r_[close[0],close[:-1]]
    return pd.DataFrame({"open":op,"high":np.maximum(op,close)+rng.uniform(.00005,.00035,n),"low":np.minimum(op,close)-rng.uniform(.00005,.00035,n),"close":close})

def build_indicators(raw):
    d=raw.copy()
    for col in ["open","high","low","close"]: d[col]=pd.to_numeric(d[col],errors="coerce")
    d=d.dropna(subset=["open","high","low","close"]).reset_index(drop=True)
    d["ema50"]=d.close.ewm(span=50,adjust=False).mean()
    d["ema200"]=d.close.ewm(span=200,adjust=False).mean()
    delta=d.close.diff()
    gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    d["rsi"]=100-100/(1+gain/loss.replace(0,np.nan))
    fast=d.close.ewm(span=12,adjust=False).mean()
    slow=d.close.ewm(span=26,adjust=False).mean()
    d["macd"]=fast-slow
    d["macd_signal"]=d.macd.ewm(span=9,adjust=False).mean()
    mid=d.close.rolling(20).mean()
    sd=d.close.rolling(20).std()
    d["bb_upper"]=mid+2*sd
    d["bb_lower"]=mid-2*sd
    body=(d.close-d.open).abs().replace(0,1e-9)
    lower=d[["open","close"]].min(axis=1)-d.low
    upper=d.high-d[["open","close"]].max(axis=1)
    d["bull_engulf"]=(d.close>d.open)&(d.close.shift(1)<d.open.shift(1))&(d.close>=d.open.shift(1))&(d.open<=d.close.shift(1))
    d["bear_engulf"]=(d.close<d.open)&(d.close.shift(1)>d.open.shift(1))&(d.close<=d.open.shift(1))&(d.open>=d.close.shift(1))
    d["bull_reject"]=(lower>body*1.8)&(d.close>d.open)
    d["bear_reject"]=(upper>body*1.8)&(d.close<d.open)
    return d

def get_signal(d):
    x=d.iloc[-1]; bull=0; bear=0; notes=[]
    if x.ema50>x.ema200: bull+=2; notes.append("EMA50 above EMA200")
    elif x.ema50<x.ema200: bear+=2; notes.append("EMA50 below EMA200")
    if x.rsi>50: bull+=1; notes.append("RSI above 50")
    elif x.rsi<50: bear+=1; notes.append("RSI below 50")
    if x.macd>x.macd_signal: bull+=1; notes.append("MACD bullish")
    elif x.macd<x.macd_signal: bear+=1; notes.append("MACD bearish")
    if x.close<=x.bb_lower: bull+=2; notes.append("Lower Bollinger touch")
    if x.close>=x.bb_upper: bear+=2; notes.append("Upper Bollinger touch")
    if bool(x.bull_engulf) or bool(x.bull_reject): bull+=2; notes.append("Bullish candle confirmation")
    if bool(x.bear_engulf) or bool(x.bear_reject): bear+=2; notes.append("Bearish candle confirmation")
    score=min(95,round(50+5*abs(bull-bear)))
    side="CALL" if bull>=5 and bull>bear and score>=threshold else "PUT" if bear>=5 and bear>bull and score>=threshold else "WAIT"
    return side,score,bull,bear,notes

if test:
    if token and chat:
        try:
            res=requests.post("https://api.telegram.org/bot"+token+"/sendMessage",json={"chat_id":chat,"text":"GABDO OTC INTELLIGENCE: test alert successful."},timeout=10)
            res.raise_for_status(); st.sidebar.success("Test alert sent.")
        except Exception as exc: st.sidebar.error(str(exc))
    else: st.sidebar.warning("Enter bot token and chat ID first.")

if mode=="Upload candle CSV":
    file=st.file_uploader("Upload OHLC candle CSV",type=["csv"])
    if file is None:
        st.info("Upload candles with open, high, low and close columns. No live Pocket Option feed is connected.")
        st.stop()
    raw=pd.read_csv(file)
else:
    raw=make_demo()
    st.warning("DEMO MODE: simulated candles only. Not live Pocket Option OTC prices. Do not trade demo signals.")
raw.columns=[str(c).strip().lower() for c in raw.columns]
missing=[c for c in ["open","high","low","close"] if c not in raw.columns]
if missing: st.error("CSV missing columns: "+", ".join(missing)); st.stop()
d=build_indicators(raw)
if len(d)<35: st.error("Please provide at least 35 valid candles."); st.stop()
if len(d)<200: st.warning("EMA200 is less stable with fewer than 200 candles.")
side,score,bull,bear,notes=get_signal(d)
c1,c2,c3,c4=st.columns(4)
c1.metric("PAIR",pair); c2.metric("TIMEFRAME",timeframe); c3.metric("RSI",round(d.rsi.iloc[-1],2)); c4.metric("SCORE",str(score)+"%")
st.subheader("Latest strategy signal")
color="#12c78a" if side=="CALL" else "#ff536b" if side=="PUT" else "#e6ad45"
st.markdown('<div style="padding:20px;border:1px solid #31415c;border-radius:14px;background:#111b2d"><h1 style="color:'+color+'">'+side+'</h1><b>Rule agreement score: '+str(score)+'%</b><p>Bull points: '+str(bull)+' | Bear points: '+str(bear)+'</p></div>',unsafe_allow_html=True)
st.write("**Strategy observations:** "+(" • ".join(notes) if notes else "No clear alignment"))
fig=go.Figure()
fig.add_trace(go.Candlestick(x=d.index,open=d.open,high=d.high,low=d.low,close=d.close,name="Candles"))
fig.add_trace(go.Scatter(x=d.index,y=d.ema50,name="EMA 50"))
fig.add_trace(go.Scatter(x=d.index,y=d.ema200,name="EMA 200"))
fig.update_layout(template="plotly_dark",height=470,xaxis_rangeslider_visible=False)
st.plotly_chart(fig,use_container_width=True)
st.subheader("Indicator values")
st.dataframe(d[["close","ema50","ema200","rsi","macd","macd_signal","bb_upper","bb_lower"]].tail(10),use_container_width=True)
st.caption("This app does not execute trades. Scores are rule-agreement scores, not win probabilities. OTC/binary-options trading is high risk; validate using historical backtests and a demo account.")
