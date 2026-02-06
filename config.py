import os

class Config:
    # This will be updated automatically by start_tunnel.py
    BASE_URL = "https://tomoko-pericarditic-regretfully.ngrok-free.dev"
    
    @classmethod
    def update_url(cls, new_url):
        cls.BASE_URL = new_url
        # Also update the environment for other scripts if needed
        os.environ["TRADESIGX_BASE_URL"] = new_url
