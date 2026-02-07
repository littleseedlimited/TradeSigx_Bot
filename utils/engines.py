import logging
from engine.ai_generator import AISignalGenerator
from data.collector import DataCollector

# Centralized Singleton Engines
# This prevents redundant memory allocations (~150MB saved)
_ai_gen = None
_data_collector = None

def get_ai_gen():
    global _ai_gen
    if _ai_gen is None:
        logging.info("🦁 Initializing Shared AI Engine (Singleton)...")
        _ai_gen = AISignalGenerator()
    return _ai_gen

def get_data_collector():
    global _data_collector
    if _data_collector is None:
        logging.info("📊 Initializing Shared Data Collector (Singleton)...")
        _data_collector = DataCollector()
    return _data_collector
