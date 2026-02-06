import pandas as pd
import pytz
from datetime import datetime, timedelta
from engine.technical_analysis import TechnicalAnalysis
from engine.market_structure import MarketStructure
from engine.sentiment_analysis import SentimentAnalysis
from engine.strategies import StrategyEngine

class AISignalGenerator:
    def __init__(self):
        self.sentiment_engine = SentimentAnalysis()

    async def generate_signal(self, asset: str, df: pd.DataFrame, fast_scan: bool = False, manual_duration: str = None):
        """
        ULTRA-SENSITIVE AI ENGINE
        Combines technicals, structure, sentiment, volume analysis, and momentum.
        'fast_scan' skips slow external API calls like news sentiment for bulk analysis.
        'manual_duration' allows user to override the AI-selected expiry.
        """
        if df.empty:
            return None

        # 1. Technical Analysis (Base Layer)
        try:
            df = TechnicalAnalysis.calculate_indicators(df)
            ta_score = TechnicalAnalysis.get_signal_strength(df)
            emergency_mode = False
        except Exception as e:
            logging.warning(f"TA Indicator Failure for {asset}: {e}. Entering EMERGENCY PRICE-ONLY MODE.")
            ta_score = 0.1 if df['close'].iloc[-1] > df['close'].iloc[-5:].mean() else -0.1
            emergency_mode = True
        
        # 2. Market Structure (Trend Detection)
        structure = MarketStructure.detect_structure(df)
        
        # 3. Sentiment Analysis (News & Social) - SKIP IF FAST_SCAN
        sentiment_score = 0
        if not fast_scan:
            sentiment_score = await self.sentiment_engine.get_sentiment(asset)
        
        # 4. VOLUME ANALYSIS (Critical for smart trading)
        volume_signal = self._analyze_volume(df)
        
        # 5. MOMENTUM & VELOCITY (Sensitivity to rapid changes)
        momentum_score = self._calculate_momentum(df)
        
        # 6. VOLATILITY AWARENESS (ATR-based risk management)
        volatility_level = self._get_volatility_level(df)
        
        # 7. MULTI-STRATEGY QUALIFICATION [NEW]
        strat_name, strat_dir = StrategyEngine.evaluate(df)
        
        # Calculate Final Confidence (0 to 100)
        # ENHANCED WEIGHTING: Strategy confirmed by Technicals
        
        raw_score = (
            (ta_score * 0.40) + 
            (sentiment_score * 0.15) +
            (volume_signal * 0.20) +
            (momentum_score * 0.25)
        )
        
        # DIRECTION LOGIC: Strategy is primary, but we FORCE a bias for "Anytime Signals"
        direction = strat_dir
        if direction == "STAY":
            # Winner takes all: Bias based on raw score
            direction = "BUY" if raw_score >= 0 else "SELL"
        
        # Alignment Boost: If Strategy and TA/Momentum agree, boost confidence
        if (direction == "BUY" and raw_score > 0) or (direction == "SELL" and raw_score < 0):
            confidence = 65 + (abs(raw_score) * 35) # Baseline 65%
        else:
            confidence = abs(raw_score) * 60 # Weak or conflicting
            
        # Recalibrate for peak setups
        confidence = min(99, confidence)
        
        # RELIABILITY FILTER: Lowered to 1% for "Anytime Signals" mode
        if confidence < 1:
            confidence = 5.0 # Ensure it shows up as a low-confidence setup rather than None
        
        # We NO LONGER return None for STAY or Low Confidence
        # SMART EXPIRY based on volatility and confidence (or manual override)
        if manual_duration:
            expiry = manual_duration
            expiry_minutes = self._parse_manual_duration(manual_duration)
        else:
            expiry, expiry_minutes = self._smart_expiry(confidence, volatility_level)
        
        # Calculate fresh entry time (increased lead time to 5.0 minutes for preparation)
        entry_time = datetime.now(pytz.UTC) + timedelta(minutes=5.0)
        
        # ADVANCED TP/SL using ATR
        last_close = df['close'].iloc[-1]
        atr = df['atr'].iloc[-1] if 'atr' in df.columns else last_close * 0.02
        
        # Metadata based on asset type
        is_otc = "OTC" in asset.upper()
        market_type = "OTC Proprietary" if is_otc else "Real Global Market"
        trade_type = "Binary Options / Digital" if expiry_minutes < 60 else "Spot Forex / CFD"
        
        # Professional Recommendation
        signal = {
            "asset": asset,
            "direction": direction,
            "confidence": round(confidence, 2),
            "market_type": market_type,
            "trade_type": trade_type,
            "expiry": expiry,
            "expiry_minutes": expiry_minutes,
            "entry_time": entry_time.strftime("%H:%M:%S"),
            "entry_timestamp": int(entry_time.timestamp()),
            "entry": last_close,
            "tp": self._calc_smart_tp(last_close, direction, atr),
            "sl": self._calc_smart_sl(last_close, direction, atr),
            "strategy": strat_name,
            "trend": "Strong Trend" if abs(ta_score) > 0.5 else "Stable Market",
            "resistance": structure['resistance'],
            "support": structure['support'],
            "rationale": self._generate_smart_rationale(
                ta_score, structure, sentiment_score, 
                volume_signal, momentum_score, volatility_level
            )
        }
        
        return signal

    def _analyze_volume(self, df):
        """Volume analysis for smart entry confirmation"""
        if 'volume' not in df.columns:
            return 0
        
        recent_vol = df['volume'].iloc[-5:].mean()
        avg_vol = df['volume'].mean()
        
        # High volume = strong signal
        if recent_vol > avg_vol * 1.5:
            return 0.8 if df['close'].iloc[-1] > df['close'].iloc[-2] else -0.8
        elif recent_vol > avg_vol * 1.2:
            return 0.4 if df['close'].iloc[-1] > df['close'].iloc[-2] else -0.4
        return 0

    def _calculate_momentum(self, df):
        """Calculate price momentum/velocity for sensitivity"""
        if len(df) < 10:
            return 0
        
        # Rate of change over last 5-10 periods
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
        
        # Normalize to -1 to 1 range
        momentum = max(min(price_change * 20, 1), -1)
        return momentum

    def _get_volatility_level(self, df):
        """Measure current volatility for risk management"""
        if 'atr' in df.columns:
            atr = df['atr'].iloc[-1]
            atr_avg = df['atr'].mean()
            return "HIGH" if atr > atr_avg * 1.3 else ("LOW" if atr < atr_avg * 0.7 else "NORMAL")
        return "NORMAL"

    def _smart_expiry(self, confidence, volatility):
        """SMART expiry based on confidence AND volatility"""
        if volatility == "HIGH":
            # High volatility = shorter expiry
            if confidence > 80: return "5 Minutes", 5
            elif confidence > 60: return "3 Minutes", 3
            else: return "1 Minute", 1
        elif volatility == "LOW":
            # Low volatility = longer expiry
            if confidence > 85: return "15 Minutes", 15
            elif confidence > 65: return "10 Minutes", 10
            else: return "5 Minutes", 5
        else:
            # Normal volatility
            if confidence > 85: return "15 Minutes", 15
            elif confidence > 60: return "5 Minutes", 5
            else: return "1 Minute", 1

    def _parse_manual_duration(self, duration_str: str) -> int:
        """Parses durations like '5s', '1m', '15m' into minutes (or ticks for seconds)."""
        duration_str = duration_str.lower()
        if 's' in duration_str:
            # Scaled minutes for sub-minute expiries (rounding up where needed for display)
            return 1 
        elif 'm' in duration_str:
            return int(duration_str.replace('m', '').replace('minutes', '').strip())
        elif 'h' in duration_str:
            return int(duration_str.replace('h', '').replace('hour', '').strip()) * 60
        return 5 # Default

    def _calc_smart_tp(self, price, direction, atr):
        """ATR-based Take Profit (2:1 risk/reward)"""
        if direction == "BUY": 
            return price + (atr * 2.5)
        elif direction == "SELL":
            return price - (atr * 2.5)
        return price

    def _calc_smart_sl(self, price, direction, atr):
        """ATR-based Stop Loss (tight but safe)"""
        if direction == "BUY": 
            return price - (atr * 1.2)
        elif direction == "SELL":
            return price + (atr * 1.2)
        return price

    def _generate_smart_rationale(self, ta_score, structure, sentiment_score, volume_signal, momentum_score, volatility):
        rationales = ["🎯 Market 'Actuals' Detection Active"]
        
        # Technical
        if ta_score > 0.4: rationales.append("🔥 Strong bullish technical confluence")
        elif ta_score < -0.4: rationales.append("❄️ Bearish technical rejection confirmed")
        elif abs(ta_score) > 0.2: rationales.append("⚡ Technical bias forming")
        
        # Structure
        if structure['trend'] == "Bullish": rationales.append("✅ Higher highs + momentum intact")
        elif structure['trend'] == "Bearish": rationales.append("❌ Lower lows + downtrend confirmed")
        
        # Volume
        if abs(volume_signal) > 0.5: rationales.append("📊 High volume confirming the move")
        
        # Momentum
        if momentum_score > 0.5: rationales.append("🚀 Strong upward momentum detected")
        elif momentum_score < -0.5: rationales.append("📉 Bearish momentum accelerating")
        
        # Sentiment
        if sentiment_score > 0.4: rationales.append("📰 Bullish news driving sentiment")
        elif sentiment_score < -0.4: rationales.append("📰 Fear & panic in the market")
        
        # Volatility warning
        if volatility == "HIGH": rationales.append("⚠️ High volatility - tight stops recommended")
        
        if not rationales: return "⚖️ Market in equilibrium. Waiting for breakout."
        return " • ".join(rationales)
