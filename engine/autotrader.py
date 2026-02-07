import asyncio
import logging
from datetime import datetime
from utils.db import DBManager, User, trade_executions
from data.collector import DataCollector
from engine.ai_generator import AISignalGenerator
from brokers.deriv_broker import DerivBroker

class AutoTrader:
    def __init__(self, ai=None, deriv=None):
        from engine.ai_generator import AISignalGenerator
        from brokers.deriv_broker import DerivBroker
        
        self.ai = ai or AISignalGenerator()
        self.deriv = deriv or DerivBroker()
        self.is_running = False

    async def start(self):
        """Starts the background autotrading loop."""
        if self.is_running:
            return
        self.is_running = True
        logging.info("AutoTrader Engine Started.")
        
        while self.is_running:
            try:
                await self._run_scan_cycle()
            except Exception as e:
                logging.error(f"AutoTrader Cycle Error: {e}")
            
            # Wait for next cycle (e.g., every 5 minutes)
            await asyncio.sleep(300)

    async def stop(self):
        self.is_running = False
        logging.info("AutoTrader Engine Stopped.")

    async def _run_scan_cycle(self):
        """Optimized: Scans unique assets once and distributes results to all users."""
        db = DBManager()
        users = db.session.query(User).filter(User.autotrade_enabled == True).all()
        
        if not users:
            db.close()
            return

        # 1. Identify unique assets to scan
        all_unique_assets = set()
        for user in users:
            assets = [a.strip() for a in user.autotrade_assets.split(",")]
            all_unique_assets.update(assets)

        if not all_unique_assets:
            db.close()
            return

        logging.info(f"AutoTrader: Batched scanning for {len(all_unique_assets)} unique assets across {len(users)} users.")

        # 2. Parallel Scanning
        async def scan_and_analyze(asset):
            try:
                df = await DataCollector.fetch_data(asset)
                if df.empty: return asset, None
                signal = await self.ai.generate_signal(asset, df, fast_scan=True)
                return asset, signal
            except Exception as e:
                logging.error(f"AutoTrader Parallel Scan Error ({asset}): {e}")
                return asset, None

        # Execute parallel scans
        scan_results = dict(await asyncio.gather(*[scan_and_analyze(a) for a in all_unique_assets]))

        # 3. Distribute Results and Execute
        today = datetime.now().strftime("%Y-%m-%d")
        for user in users:
            user_assets = [a.strip() for a in user.autotrade_assets.split(",")]
            for asset in user_assets:
                signal = scan_results.get(asset)
                if not signal: continue

                # Decision Logic
                if signal['confidence'] >= user.autotrade_min_confidence:
                    # Check daily limit
                    trade_count = db.session.query(trade_executions).filter(
                        trade_executions.c.user_id == str(user.telegram_id),
                        trade_executions.c.timestamp >= datetime.strptime(today, "%Y-%m-%d")
                    ).count()
                    
                    if trade_count < user.autotrade_max_trades:
                        logging.info(f"AutoTrader: Executing {signal['direction']} for {user.telegram_id} on {asset} (Conf: {signal['confidence']}%)")
                        await self._execute_for_user(user, signal)
        
        db.close()

    async def _execute_for_user(self, user, signal):
        """Executes the trade based on user's broker connectivity."""
        # For now, we only have Deriv fully implemented for autotrading
        # Pocket Option is instruction-only and doesn't support API execution
        
        amount = user.risk_per_trade # Use user's risk setting as amount for binary
        if amount <= 0: amount = 1.0 # Default fallback
        
        # Execute on Deriv
        result = await self.deriv.execute_trade(
            symbol=signal['asset'],
            direction=signal['direction'],
            amount=amount
        )
        
        if result['status'] == "success":
            logging.info(f"AutoTrader: Trade successful for {user.telegram_id}: {result['contract_id']}")
            # We could log this to trade_executions table if needed, 
            # but currently we don't have a direct helper in DBManager for it yet.
        else:
            logging.warning(f"AutoTrader: Trade failed for {user.telegram_id}: {result.get('message')}")

# Global instance
auto_trader = AutoTrader()
