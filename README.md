# GABDO OTC INTELLIGENCE

A Streamlit dashboard for analysing OHLC candle data with a configurable technical strategy.

## Included
- OTC pair and timeframe selectors
- EMA 50/200 and SMA 40
- RSI, MACD, Stochastic, Awesome Oscillator
- Bulls Power, Bears Power and Williams %R
- Bollinger context and candlestick engulfing/rejection checks
- CALL / PUT / WAIT rule-agreement score
- CSV OHLC upload and clearly labelled simulated demo mode
- Optional Telegram test message

## Data limitation
This starter version does not connect to an official Pocket Option OTC market feed. Supply candle CSV data from a trusted source. Demo mode is simulated, not live market data. The pair and timeframe selectors label the analysis; they do not transform candle data.

## Run
Install dependencies with `pip install -r requirements.txt`, then run `streamlit run app.py`.

CSV columns required: `open, high, low, close`.

The app does not execute trades. Scores are indicator agreement, not probabilities or guaranteed win rates.
