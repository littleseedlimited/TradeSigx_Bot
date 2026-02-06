import pandas as pd
import ta
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands

class TechnicalAnalysis:
    @staticmethod
    def calculate_indicators(df: pd.DataFrame):
        """
        Calculates a standard set of technical indicators for the dataframe using the 'ta' library.
        Expected columns: open, high, low, close, volume
        """
        # Ensure columns are float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].astype(float)
        
        close = df['close']
        high = df['high']
        low = df['low']

        # RSI
        df['RSI_14'] = RSIIndicator(close, window=14).rsi()
        
        # MACD
        macd = MACD(close, window_slow=26, window_fast=12, window_sign=9)
        df['MACD_12_26_9'] = macd.macd()
        df['MACDs_12_26_9'] = macd.macd_signal()
        
        # Bollinger Bands
        bb = BollingerBands(close, window=20, window_dev=2)
        df['BBL_20_2.0'] = bb.bollinger_lband()
        df['BBM_20_2.0'] = bb.bollinger_mavg()
        df['BBU_20_2.0'] = bb.bollinger_hband()
        
        # EMA Suite
        df['EMA_9'] = EMAIndicator(close, window=9).ema_indicator()
        df['EMA_21'] = EMAIndicator(close, window=21).ema_indicator()
        df['EMA_50'] = EMAIndicator(close, window=50).ema_indicator()
        df['EMA_200'] = EMAIndicator(close, window=200).ema_indicator()
        
        # Stochastic
        stoch = StochasticOscillator(high, low, close, window=14, smooth_window=3)
        df['STOCHk_14_3_3'] = stoch.stoch()
        df['STOCHd_14_3_3'] = stoch.stoch_signal()
        
        # ADX (Trend Strength)
        adx = ADXIndicator(high, low, close, window=14)
        df['ADX_14'] = adx.adx()
        df['ADX_pos'] = adx.adx_pos()
        df['ADX_neg'] = adx.adx_neg()
        
        # ATR (Volatility)
        from ta.volatility import AverageTrueRange
        df['atr'] = AverageTrueRange(high, low, close, window=14).average_true_range()
        
        return df

    @staticmethod
    def get_signal_strength(df: pd.DataFrame):
        """
        Determines the strength of the move based on technicals.
        Returns a score from -1 (Strong Sell) to 1 (Strong Buy).
        Highly sensitive to trend strength and momentum.
        """
        if df.empty or len(df) < 2:
            return 0
            
        last_row = df.iloc[-1]
        score = 0
        total_weight = 0
        
        # 0. THE GOLDEN FILTER: EMA 50/200 Trend Alignment
        # We determine the "Bias" based on EMA location
        bias = 0
        if all(k in last_row for k in ['close', 'EMA_50']):
            if not pd.isna(last_row.get('EMA_200')):
                if last_row['close'] > last_row['EMA_50'] > last_row['EMA_200']: bias = 1 
                elif last_row['close'] < last_row['EMA_50'] < last_row['EMA_200']: bias = -1 
            else:
                # Fallback to EMA_50 only if EMA_200 is missing
                if last_row['close'] > last_row['EMA_50']: bias = 0.5 # Weak Bullish
                else: bias = -0.5 # Weak Bearish
        
        # 1. RSI (Weight: 2.0)
        if 'RSI_14' in last_row and not pd.isna(last_row['RSI_14']):
            rsi = last_row['RSI_14']
            rsi_delta = (rsi - 50) / 20 
            # In a bullish bias, we favor higher RSI; in bearish, lower.
            if (bias == 1 and rsi_delta > 0) or (bias == -1 and rsi_delta < 0):
                score += rsi_delta * 2.5 # Boosted
            else:
                score += rsi_delta * 1.5
            total_weight += 2.0
            
            # Oversold/Overbought Reentry logic (Trend-Aligned)
            if bias == 1 and rsi < 40: score += 1.5; total_weight += 1.0 # Buy the dip
            elif bias == -1 and rsi > 60: score -= 1.5; total_weight += 1.0 # Sell the rip
        
        # 2. MACD (Weight: 2.0) - Trend Confirmation
        if 'MACD_12_26_9' in last_row and 'MACDs_12_26_9' in last_row:
            if not pd.isna(last_row['MACD_12_26_9']) and not pd.isna(last_row['MACDs_12_26_9']):
                macd_val = last_row['MACD_12_26_9']
                signal_val = last_row['MACDs_12_26_9']
                cross_strength = (macd_val - signal_val) / (abs(macd_val) + abs(signal_val) + 0.0001)
                
                # Only give full weight if cross aligns with Bias
                if (bias == 1 and cross_strength > 0) or (bias == -1 and cross_strength < 0):
                    score += cross_strength * 2.0
                else:
                    score += cross_strength * 0.5 # Diminished if against trend
                total_weight += 2.0
        
        # 3. EMA Confluence (Weight: 2.0) - HEAVIER WEIGHT
        if 'EMA_50' in last_row and not pd.isna(last_row['EMA_50']):
            price_dist = (last_row['close'] - last_row['EMA_50']) / last_row['EMA_50']
            ema_score = max(min(price_dist * 100, 2.0), -2.0)
            score += ema_score
            total_weight += 2.0
            
        # 4. ADX Trend Filtering (Weight: 1.5)
        if 'ADX_14' in last_row and not pd.isna(last_row['ADX_14']):
            adx = last_row['ADX_14']
            if adx > 25: # Strong trend present
                strength = (last_row['ADX_pos'] - last_row['ADX_neg']) / 50
                score += strength * 1.5
                total_weight += 1.5
            else:
                # Weak trend, penalize non-reversion scores
                total_weight += 1.0
                
        # 5. Stochastic (Weight: 1.5) - TREND RE-ENTRY ONLY
        if 'STOCHk_14_3_3' in last_row and not pd.isna(last_row['STOCHk_14_3_3']):
            stoch = last_row['STOCHk_14_3_3']
            # Re-entry: Stochastic oversold in a BULL trend
            if bias == 1 and stoch < 30:
                score += 1.5
                total_weight += 1.5
            # Re-entry: Stochastic overbought in a BEAR trend
            elif bias == -1 and stoch > 70:
                score -= 1.5
                total_weight += 1.5

        if total_weight == 0: return 0
        final_score = score / total_weight
        
        # FINAL SANITY CHECK: If bias is strong, don't allow counter-trend signals to exceed 0.3 strength
        if bias == 1 and final_score < -0.2: final_score = -0.1
        if bias == -1 and final_score > 0.2: final_score = 0.1
        
        return max(min(final_score, 1), -1)
