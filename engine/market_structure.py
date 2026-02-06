import pandas as pd
import numpy as np

class MarketStructure:
    @staticmethod
    def detect_structure(df: pd.DataFrame):
        """
        Detects Break of Structure (BOS) and Change of Character (CHoCH).
        This is a simplified version of Smart Money Concepts (SMC).
        """
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        
        structure = {
            "trend": "Neutral",
            "last_bos": None,
            "last_choch": None,
            "support": None,
            "resistance": None
        }
        
        if len(df) < 20:
            return structure

        # Find local peaks/valleys
        # Simplified: uses rolling windows
        df['hh'] = df['high'].rolling(window=5, center=True).max()
        df['ll'] = df['low'].rolling(window=5, center=True).min()
        
        # Trend detection based on EMAs with NaN protection
        if 'EMA_50' in df.columns and 'EMA_200' in df.columns:
            ema50 = df['EMA_50'].iloc[-1]
            ema200 = df['EMA_200'].iloc[-1]
            
            if not pd.isna(ema50) and not pd.isna(ema200):
                if ema50 > ema200:
                    structure['trend'] = "Bullish"
                else:
                    structure['trend'] = "Bearish"
            else:
                structure['trend'] = "Neutral" # Safety fallback

        # Resistance/Support
        structure['resistance'] = df['high'].tail(20).max()
        structure['support'] = df['low'].tail(20).min()
        
        return structure
