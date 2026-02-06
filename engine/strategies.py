import pandas as pd
import numpy as np

class StrategyEngine:
    @staticmethod
    def evaluate(df: pd.DataFrame):
        """
        Evaluates the market using 5 distinct quantitative strategies.
        Returns the name of the strongest qualifying strategy and its direction.
        """
        if df.empty or len(df) < 20:
            return "No Strategy Qualified", "STAY"

        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # TREND BIAS FILTER
        bias = 0
        if 'EMA_50' in last and 'EMA_200' in last:
            if last['close'] > last['EMA_50'] > last['EMA_200']: bias = 1
            elif last['close'] < last['EMA_50'] < last['EMA_200']: bias = -1

        results = []

        # 1. Trend Follower (EMA Cross) + ADX Confirmation
        if 'EMA_9' in last and 'EMA_21' in last:
            adx = last.get('ADX_14', 0)
            if prev['EMA_9'] <= prev['EMA_21'] and last['EMA_9'] > last['EMA_21'] and adx > 15:
                results.append(("Trend Follower (EMA Cross)", "BUY", 0.85))
            elif prev['EMA_9'] >= prev['EMA_21'] and last['EMA_9'] < last['EMA_21'] and adx > 15:
                results.append(("Trend Follower (EMA Cross)", "SELL", 0.85))

        # 2. Mean Reversion (Bollinger + RSI) + Trend Exhaustion
        if all(k in last for k in ['RSI_14', 'BBL_20_2.0', 'BBU_20_2.0']):
            # Bullish Reversal: Relaxed RSI 35/65
            if last['close'] < last['BBL_20_2.0'] and last['RSI_14'] < 35 and bias != -1:
                results.append(("Mean Reversion (BB+RSI)", "BUY", 0.8))
            elif last['close'] > last['BBU_20_2.0'] and last['RSI_14'] > 65 and bias != 1:
                results.append(("Mean Reversion (BB+RSI)", "SELL", 0.8))

        # 3. Momentum Breakout (ADX + Volume)
        if 'ADX_14' in last and 'volume' in last:
            avg_vol = df['volume'].tail(20).mean()
            if last['ADX_14'] > 20 and last['volume'] > avg_vol * 1.3:
                # Must align with Bias
                dir = "BUY" if (last['close'] > prev['close'] and bias != -1) else ("SELL" if (last['close'] < prev['close'] and bias != 1) else "STAY")
                if dir != "STAY":
                    results.append(("Momentum Breakout (ADX+Vol)", dir, 0.9))

        # 4. Smart Money (BOS / Structure) - Increased to 0.3%
        lookback = 30
        upper_band = df['high'].iloc[-lookback:-1].max()
        lower_band = df['low'].iloc[-lookback:-1].min()
        
        if last['close'] > upper_band * 1.003 and bias != -1:
            results.append(("Smart Money (Structure BOS)", "BUY", 0.8))
        elif last['close'] < lower_band * 0.997 and bias != 1:
            results.append(("Smart Money (Structure BOS)", "SELL", 0.8))

        # 5. Scalping Pulse (Stoch + MACD) - Trend Only
        if all(k in last for k in ['STOCHk_14_3_3', 'MACD_12_26_9', 'MACDs_12_26_9']):
            if bias != -1 and last['STOCHk_14_3_3'] < 35 and last['MACD_12_26_9'] > last['MACDs_12_26_9']:
                results.append(("Scalping Pulse (Stoch+MACD)", "BUY", 0.75))
            elif bias != 1 and last['STOCHk_14_3_3'] > 65 and last['MACD_12_26_9'] < last['MACDs_12_26_9']:
                results.append(("Scalping Pulse (Stoch+MACD)", "SELL", 0.75))

        if not results:
            return "Stable Market Scan", "STAY"

        # CONFLICT RESOLUTION
        directions = [r[1] for r in results]
        if "BUY" in directions and "SELL" in directions:
            return "High Volatility Conflict", "STAY"

        results.sort(key=lambda x: x[2], reverse=True)
        return results[0][0], results[0][1]
