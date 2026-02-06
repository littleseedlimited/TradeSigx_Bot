class PocketOptionBroker:
    def __init__(self):
        self.user_id = None

    def get_execution_instructions(self, symbol: str, direction: str, amount: float, duration: str):
        """
        Returns manual execution instructions for Pocket Option since it lacks a public API.
        """
        return {
            "platform": "Pocket Option",
            "symbol": symbol,
            "direction": direction,
            "amount": amount,
            "duration": duration,
            "instruction": f"Open Pocket Option Web/App, select {symbol}, set duration to {duration}, and enter a {direction} trade for ${amount}."
        }
