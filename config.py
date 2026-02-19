import os

class Config:
    # DEFINITIVE BASE URL RESOLUTION
    # 1. Check TRADESIGX_BASE_URL (Manual override)
    # 2. Check RENDER_EXTERNAL_URL (Automatic on Render)
    # 3. Default to hardcoded stable tunnel
    BASE_URL = os.getenv("TRADESIGX_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "https://tradesigx-v8-gold-pro.serveo.net"
    
    @classmethod
    def update_url(cls, new_url):
        cls.BASE_URL = new_url
        os.environ["TRADESIGX_BASE_URL"] = new_url
