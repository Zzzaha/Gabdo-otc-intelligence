import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="GABDO OTC INTELLIGENCE",page_icon="📡",layout="wide")
st.title("📡 GABDO OTC INTELLIGENCE")
st.caption("Technical-strategy scanner • CALL / PUT / WAIT")
PAIRS=["EUR/USD OTC","GBP/USD OTC","USD/JPY OTC","AUD/USD OTC","EUR/GBP OTC","USD/CAD OTC","NZD/USD OTC","GBP/JPY OTC"]
with st.sidebar:
    pair=st.selectbox("OTC pair",PAIRS)
    timeframe=st.selectbox("Chart timeframe",["5 seconds","15 seconds","30 seconds","1 minute","5 minutes"])
    source=st.radio("Candle source",["Upload CSV","Simulated demo"])
    threshold=st.slider("Minimum rule agreement",50,95,70,5)
    st.subheader("Telegram")
    token=st.text_input("Bot token",type="password")
    chat=st.text_input("Chat ID")
    test=st.button("Send test message")
if test:
    if token and chat:
        try:
            r=requests.post("https://api.telegram.org/bot"+token+"/sendMessage",json={"chat_id":chat,"text":"GABDO OTC INTELLIGENCE test alert"},timeout=10); r.raise_for_status(); st.success("Telegram test sent.")
        except Exception as e: st.error(str(e))
    else: st.warning("Enter bot token and chat ID.")
def demo(n=260):
    rng=np.random.default_rng(); c=1.08+rng.normal(0,.0004,n).cumsum(); o=np.r_[c[0],c[:-1]]
    return pd.DataFrame({"open":o,"high":np.maximum(o,c)+rng.uniform(.00005,.0003,n),"low":np.minimum(o,c)-rng.uniform(.00005,.0003,n),"close":c})
if source=="Upload CSV":
    f=st.file_uploader("OHLC candle CSV",type="csv")
    if f is None: st.info("Upload candles with open, high, low, close columns."); st.stop()
    df=pd.read_csv(f)
else:
    df=demo(); st.warning("SIMULATED DATA ONLY — not live Pocket Option prices. Do not trade these demo signals.")
df.columns=[str(x).strip().lower() for x in df.columns]
need=["open","high","low","close"]
if any(x not in df for x in need): st.error("CSV must contain open, high, low, close."); st.stop()
for x in need: df[x]=pd.to_numeric(df[x],errors="coerce")
df=df.dropna(subset=need).reset_index(drop=True)
if len(df)<50: st.error("Please provide at least 50 candles."); st.stop()
c=df.close; df["ema50"]=c.ewm(span=50,adjust=False).mean(); df["ema200"]=c.ewm(span=200,adjust=False).mean(); df["sma40"]=c.rolling(40).mean()
delta=c.diff(); up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); dn=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean(); df["rsi"]=100-100/(1+up/dn.replace(0,np.nan))
m=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean(); df["macd"]=m; df["macd_signal"]=m.ewm(span=9,adjust=False).mean()
lo=df.low.rolling(14).min(); hi=df.high.rolling(14).max(); df["stoch"]=100*(c-lo)/(hi-lo).replace(0,np.nan); df["stoch_signal"]=df.stoch.rolling(3).mean(); df["williams_r"]=-100*(hi-c)/(hi-lo).replace(0,np.nan)
typ=(df.high+df.low)/2; df["ao"]=typ.rolling(5).mean()-typ.rolling(34).mean(); ema13=c.ewm(span=13,adjust=False).mean(); df["bulls_power"]=df.high-ema13; df["bears_power"]=df.low-ema13
body=(df.close-df.open).abs().replace(0,1e-9); lw=df[["open","close"]].min(axis=1)-df.low; uw=df.high-df[["open","close"]].max(axis=1)
df["bull_reject"]=(lw>1.8*body)&(c>df.open); df["bear_reject"]=(uw>1.8*body)&(c<df.open)
df["bull_engulf"]=(c>df.open)&(df.close.shift()>df.open.shift())&(c>df.open.shift())&(df.open<df.close.shift())
df["bear_engulf"]=(c<df.open)&(df.close.shift()<df.open.shift())&(c<df.open.shift())&(df.open>df.close.shift())
x=df.iloc[-1]; bull=0; bear=0; notes=[]
rules=[(x.ema50>x.ema200,2,"EMA trend"),(x.close>x.sma40,1,"SMA40"),(x.rsi>50,1,"RSI"),(x.macd>x.macd_signal,1,"MACD"),(x.stoch>x.stoch_signal,1,"Stochastic"),(x.ao>0,1,"Awesome Oscillator"),(x.bulls_power>abs(x.bears_power),1,"Bulls/Bears Power")]
for ok,w,label in rules:
    if ok: bull+=w; notes.append(label+" bullish")
    else: bear+=w; notes.append(label+" bearish")
if x.bull_reject or x.bull_engulf: bull+=2; notes.append("Bullish candle confirmation")
if x.bear_reject or x.bear_engulf: bear+=2; notes.append("Bearish candle confirmation")
if x.williams_r < -80: bull+=1; notes.append("Williams %R oversold")
elif x.williams_r > -20: bear+=1; notes.append("Williams %R overbought")
score=round(100*max(bull,bear)/max(1,bull+bear))
signal="CALL" if bull>=7 and bull>bear and score>=threshold else "PUT" if bear>=7 and bear>bull and score>=threshold else "WAIT"
a,b,d,e=st.columns(4); a.metric("PAIR",pair); b.metric("TIMEFRAME",timeframe); d.metric("RSI",f"{x.rsi:.1f}"); e.metric("RULE AGREEMENT",f"{score}%")
st.header("Latest signal: "+signal); st.write("Bull points:",bull,"| Bear points:",bear); st.write(" • ".join(notes))
fig=go.Figure(); fig.add_trace(go.Candlestick(x=df.index,open=df.open,high=df.high,low=df.low,close=df.close,name="Candles")); fig.add_trace(go.Scatter(x=df.index,y=df.ema50,name="EMA50")); fig.add_trace(go.Scatter(x=df.index,y=df.sma40,name="SMA40")); fig.update_layout(template="plotly_dark",height=450,xaxis_rangeslider_visible=False); st.plotly_chart(fig,use_container_width=True)
st.subheader("Indicator values"); st.dataframe(df[["close","ema50","ema200","sma40","rsi","macd","macd_signal","stoch","williams_r","ao","bulls_power","bears_power"]].tail(10),use_container_width=True)
st.caption("No trade execution. Rule agreement is not a win probability. OTC/binary options are high risk; test with historical data and a demo account first.")
