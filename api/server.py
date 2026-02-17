from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, List
import json
import asyncio
from datetime import datetime
import logging
import os

app = FastAPI(title="TradeSigx API", version="2.0.0")

# Global instances for shared memory (Consolidation)
from utils.engines import get_ai_gen, get_data_collector
ai_gen = get_ai_gen()
data_collector = get_data_collector()

# Enable CORS for Telegram Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files from webapp directory at root
webapp_path = os.path.join(os.getcwd(), "webapp")
app.mount("/static", StaticFiles(directory=webapp_path), name="static")

@app.get("/")
async def serve_index():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(webapp_path, "index.html"))

@app.get("/style.css")
async def serve_style():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(webapp_path, "style.css"))

@app.get("/app.js")
async def serve_js():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(webapp_path, "app.js"))

# Also handle common assets directly if needed or keep /static

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logging.info(f"User {user_id} connected to WebSocket")
        
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logging.info(f"User {user_id} disconnected")
            
    async def send_signal(self, user_id: str, signal: dict):
        """Send signal to specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json({
                    "type": "signal",
                    "data": signal,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logging.error(f"Error sending to {user_id}: {e}")
                self.disconnect(user_id)
                
    async def broadcast(self, message: dict):
        """Broadcast to all connected users"""
        disconnected = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except:
                disconnected.append(user_id)
        
        for user_id in disconnected:
            self.disconnect(user_id)

manager = ConnectionManager()


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive with heartbeat
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(user_id)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/signals/{user_id}")
async def get_user_signals(user_id: str, limit: int = 10):
    """Fetch user's recent signals from database"""
    from utils.db import init_db, SignalHistory
    
    db = init_db()
    try:
        signals = db.session.query(SignalHistory).order_by(SignalHistory.id.desc()).limit(limit).all()
    finally:
        db.close()
    
    return {
        "user_id": user_id,
        "signals": [
            {
                "asset": s.asset,
                "direction": s.direction,
                "entry_price": s.entry_price,
                "tp": s.tp,
                "sl": s.sl,
                "confidence": s.confidence,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None
            }
            for s in signals
        ]
    }

@app.post("/api/execute-trade")
async def execute_trade(trade_data: dict):
    """Handle trade execution from Mini App"""
    # This will integrate with broker APIs in production
    return {
        "status": "success",
        "order_id": f"ORD_{int(datetime.now().timestamp())}",
        "asset": trade_data.get("asset"),
        "direction": trade_data.get("direction"),
        "executed_at": datetime.now().isoformat()
    }

@app.get("/api/market-scan")
async def market_scan():
    # Use shared global ai_gen and data_collector
    from utils.engines import get_ai_gen, get_data_collector
    this_ai_gen = get_ai_gen()
    this_data_collector = get_data_collector()
    
    # Priority assets (High Return / Popular)
    assets_to_scan = [
        # Forex OTC
        ("EURUSD=X", "forex"), ("GBPUSD=X", "forex"), ("USDJPY=X", "forex"),
        # Crypto
        ("BTC/USDT", "crypto"), ("ETH/USDT", "crypto"), ("SOL/USDT", "crypto"),
        # Synthetics
        ("R_100", "synthetic"), ("R_75", "synthetic"), ("C1000", "synthetic"), ("B1000", "synthetic"),
        # Commodities
        ("GC=F", "forex"), # Gold
    ]

    async def scan_asset(symbol, asset_type):
        try:
            if asset_type == "forex":
                df = await data_collector.fetch_data(symbol, asset_type)
            elif asset_type == "crypto":
                df = await data_collector.get_crypto_data(symbol)
            elif asset_type == "synthetic":
                df = await data_collector.get_synthetic_data(symbol)
            else:
                return None
                
            if df.empty: return None
            
            signal = await this_ai_gen.generate_signal(symbol, df)
            if signal and signal['confidence'] >= 85:
                return signal
        except Exception as e:
            logging.error(f"Scan error for {symbol}: {e}")
        return None

    # Run scans in parallel
    tasks = [scan_asset(s, t) for s, t in assets_to_scan]
    results = await asyncio.gather(*tasks)
    
    # Filter valid signals
    high_conf_signals = [r for r in results if r is not None]
    
    # Sort by confidence descending
    high_conf_signals.sort(key=lambda x: x['confidence'], reverse=True)
    
    return {
        "count": len(high_conf_signals),
        "signals": high_conf_signals[:10] # Top 10 as requested
    }

@app.post("/api/internal/push-signal")
async def push_signal_internal(payload: dict):
    """Internal endpoint for Bot to push signals to Mini App"""
    user_id = payload.get("user_id")
    signal = payload.get("signal")
    if user_id and signal:
        await manager.send_signal(str(user_id), signal)
        return {"status": "success"}
    return {"status": "error", "message": "Missing user_id or signal"}

# --- ADMIN MANAGEMENT ENDPOINTS ---

@app.get("/api/admin/users")
async def admin_get_users(admin_id: str):
    """Fetch all users for the Admin Dashboard"""
    from utils.db import init_db, User, SUPER_ADMIN_ID
    if admin_id != SUPER_ADMIN_ID:
        raise HTTPException(status_code=403, detail="Unauthorized Access")
    
    db = init_db()
    try:
        users = db.get_all_users()
        return [
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "username": u.username,
                "full_name": u.full_name,
                "email": u.email,
                "subscription_plan": u.subscription_plan,
                "kyc_status": u.kyc_status,
                "is_registered": u.is_registered,
                "is_admin": u.is_admin,
                "is_banned": u.is_banned,
                "joined_at": u.joined_at.isoformat() if u.joined_at else None
            }
            for u in users
        ]
    finally:
        db.close()

@app.post("/api/admin/user-action")
async def admin_user_action(payload: dict):
    """Perform CRUD action on a user (ban, promote, delete)"""
    from utils.db import init_db, User, SUPER_ADMIN_ID, SignalHistory, TradeExecution, BrokerAccount
    admin_id = payload.get("admin_id")
    target_id = payload.get("target_id")
    action = payload.get("action") # ban, unban, promote, demote, delete
    
    if admin_id != SUPER_ADMIN_ID:
        raise HTTPException(status_code=403, detail="Unauthorized Access")
    
    db = init_db()
    try:
        user = db.get_user_by_telegram_id(target_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        if action == "ban":
            user.is_banned = True
            user.ban_reason = payload.get("reason", "Violated terms")
        elif action == "unban":
            user.is_banned = False
        elif action == "promote":
            user.is_admin = True
        elif action == "demote":
            user.is_admin = False
        elif action == "delete":
            # Cascading deletion for SQLite (manual because of how models are structured)
            db.session.query(TradeExecution).filter(TradeExecution.user_id == target_id).delete()
            db.session.query(BrokerAccount).filter(BrokerAccount.user_id == user.id).delete()
            # Note: SignalHistory is global, not user-specific in current schema
            db.session.delete(user)
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
        db.commit()
        return {"status": "success", "message": f"Action {action} performed on {target_id}"}
    finally:
        db.close()

# Function to be called from bot handlers
async def push_signal_to_miniapp(user_id: str, signal: dict):
    """Called by bot to push signal to Mini App"""
    await manager.send_signal(user_id, signal)

# Removed uvicorn.run to allow main.py to handle startup
