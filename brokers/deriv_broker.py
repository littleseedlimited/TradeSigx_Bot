import os
import asyncio
from deriv_api import DerivAPI

class DerivBroker:
    def __init__(self):
        self.app_id = os.getenv("DERIV_APP_ID")
        self.token = os.getenv("DERIV_API_TOKEN")

    async def _get_api(self):
        if not self.app_id:
            raise ValueError("DERIV_APP_ID not found in environment.")
        return DerivAPI(app_id=self.app_id)

    async def execute_trade(self, symbol: str, direction: str, amount: float):
        """
        Executes a trade on Deriv (Synthetic Indices).
        Direction: BUY or SELL
        """
        if not self.token:
            return {"status": "error", "message": "Deriv API Token missing."}

        try:
            api = await self._get_api()
            # Authorize
            await api.authorize(self.token)
            
            # Determine contract type
            # Simplification: Use 'CALL' for BUY and 'PUT' for SELL (Digital options)
            contract_type = 'CALL' if direction == "BUY" else 'PUT'
            
            # Buy contract
            proposal = await api.proposal({
                "proposal": 1,
                "amount": amount,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": 5,
                "duration_unit": "m", # 5 minutes
                "symbol": symbol
            })
            
            buy = await api.buy({"buy": proposal['proposal']['id'], "price": amount})
            return {"status": "success", "contract_id": buy['buy']['contract_id']}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            if 'api' in locals():
                await api.clear_api()
