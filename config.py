import os

class Config:
    # Prioritize Environment Variables for Production (Render)
    # Falling back to stable tunnel for local development
    BASE_URL = os.getenv(
        "TRADESIGX_BASE_URL", 
        os.getenv("RENDER_EXTERNAL_URL", "https://tradesigx-v8-gold-pro.serveo.net")
    )
    
    @classmethod
    def update_url(cls, new_url):
        cls.BASE_URL = new_url
        os.environ["TRADESIGX_BASE_URL"] = new_url
