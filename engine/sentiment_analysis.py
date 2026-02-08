import os
import httpx
import asyncio
import time
from newsapi import NewsApiClient

class SentimentAnalysis:
    def __init__(self):
        self.api_key = os.getenv("NEWS_API_KEY")
        self._sentiment_cache = {} # Cache sentiment results
        self.SENTIMENT_TTL = 900 # 15 minutes
        self.MAX_SENTIMENT_CACHE = 20 # Hard limit for 512MB RAM
        if self.api_key:
            self.newsapi = NewsApiClient(api_key=self.api_key)
        else:
            self.newsapi = None

    async def _fetch_news_safe(self, query: str):
        """Thread-safe news fetching"""
        if not self.newsapi: return {}
        return await asyncio.to_thread(self.newsapi.get_everything, q=query, language='en', sort_by='relevancy', page_size=5)

    async def get_sentiment(self, query: str):
        """
        Fetches news for a query and returns a simple bullish/bearish score.
        Score: -1 (Negative) to 1 (Positive)
        """
        if not self.newsapi:
            return 0 # Neutral if no API key
            
        # Check Cache
        if query in self._sentiment_cache:
            cache_entry = self._sentiment_cache[query]
            if time.time() - cache_entry['timestamp'] < self.SENTIMENT_TTL:
                return cache_entry['score']

        try:
            # Fetch headlines (Offloaded to thread)
            news = await self._fetch_news_safe(query)
            articles = news.get('articles', [])
            
            if not articles:
                self._sentiment_cache[query] = {'score': 0, 'timestamp': time.time()}
                return 0
                
            # Basic keyword-based sentiment (can be improved with LLM)
            bullish_words = ['gain', 'rise', 'growth', 'bullish', 'high', 'surge', 'recovery', 'uptrend']
            bearish_words = ['drop', 'fall', 'loss', 'bearish', 'low', 'plunge', 'crash', 'down', 'recession']
            
            score = 0
            for art in articles:
                text = (art['title'] + " " + str(art['description'])).lower()
                for word in bullish_words:
                    if word in text: score += 1
                for word in bearish_words:
                    if word in text: score -= 1
            
            # Normalize
            final_score = max(-1, min(1, score / 10))
            
            # Update Cache (with cap enforcement)
            if len(self._sentiment_cache) >= self.MAX_SENTIMENT_CACHE:
                # Remove oldest entry
                oldest_key = min(self._sentiment_cache.keys(), key=lambda k: self._sentiment_cache[k]['timestamp'])
                del self._sentiment_cache[oldest_key]
                
            self._sentiment_cache[query] = {'score': final_score, 'timestamp': time.time()}
            return final_score
            
        except Exception as e:
            print(f"Sentiment Error: {e}")
            return 0
