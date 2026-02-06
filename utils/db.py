import os
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
import datetime

Base = declarative_base()

# Super Admin Telegram ID
SUPER_ADMIN_ID = "1241907317"  # @origichidiah

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, index=True)
    username = Column(String)
    
    # Authentication & Profile
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True)
    phone = Column(String, nullable=True)
    country = Column(String, nullable=True)
    is_registered = Column(Boolean, default=False)  # Completed signup
    registration_step = Column(String, default="start")  # Tracks signup progress
    terms_accepted = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Subscription & Monetization
    subscription_plan = Column(String, default="free")  # free, basic, pro, vip
    plan_expires_at = Column(DateTime, nullable=True)
    signals_used_today = Column(Integer, default=0)
    last_signal_date = Column(String, nullable=True)  # For daily reset
    
    # KYC Verification
    kyc_status = Column(String, default="not_submitted")  # not_submitted, pending, approved, rejected
    kyc_id_document = Column(String, nullable=True)  # File ID or URL
    kyc_selfie = Column(String, nullable=True)  # File ID or URL
    kyc_submitted_at = Column(DateTime, nullable=True)
    kyc_reviewed_at = Column(DateTime, nullable=True)
    kyc_rejection_reason = Column(String, nullable=True)
    
    # Admin Privileges
    is_admin = Column(Boolean, default=False)
    is_super_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(String, nullable=True)
    
    # Risk Management Settings
    default_lot = Column(Float, default=0.01)
    risk_per_trade = Column(Float, default=1.0)
    max_daily_loss = Column(Float, default=5.0)
    
    # Wallet System
    wallet_balance = Column(Float, default=0.0)
    wallet_currency = Column(String, default="USD")
    wallet_address = Column(String, unique=True, nullable=True)
    timezone = Column(String, default="UTC")
    notifications_enabled = Column(Boolean, default=True)
    bulk_scan_config = Column(String, default="BTC/USDT,ETH/USDT,GC=F,EURUSD=X,GBPUSD=X")
    external_wallets = Column(Text, nullable=True) # JSON string: {"metamask": "0x...", "phantom": "..."}
    
    # Autotrading Settings
    autotrade_enabled = Column(Boolean, default=False)
    autotrade_min_confidence = Column(Float, default=75.0)
    autotrade_max_trades = Column(Integer, default=5)
    autotrade_assets = Column(String, default="BTC/USDT,ETH/USDT,GC=F")

class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)  # free, basic, pro, vip
    display_name = Column(String)
    price_usd = Column(Float)
    signals_per_day = Column(Integer)  # -1 for unlimited
    features = Column(Text)  # JSON string of features
    is_active = Column(Boolean, default=True)

class PaymentTransaction(Base):
    __tablename__ = 'payment_transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Float)
    currency = Column(String, default="USD")
    payment_method = Column(String)  # paystack, crypto, bank_transfer, telegram_stars
    transaction_ref = Column(String, unique=True)
    status = Column(String, default="pending")  # pending, completed, failed
    plan_purchased = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON for extra data

class BrokerAccount(Base):
    __tablename__ = 'broker_accounts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    broker_name = Column(String)
    api_key = Column(String)
    api_secret = Column(String)
    app_id = Column(String)
    is_active = Column(Boolean, default=True)

class SignalHistory(Base):
    __tablename__ = 'signal_history'
    id = Column(Integer, primary_key=True)
    asset = Column(String)
    direction = Column(String)
    entry_price = Column(Float)
    tp = Column(Float)
    sl = Column(Float)
    confidence = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class TradeExecution(Base):
    __tablename__ = 'trade_executions'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    asset = Column(String)
    direction = Column(String)
    amount = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    status = Column(String, default="OPEN")
    pnl = Column(Float, default=0.0)
    contract_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# Global Database Engine & Session Factory
# Production Database Path (for Render Persistent Disk)
db_path = 'tradesigx.db'
if os.path.exists('/data'):
    db_path = '/data/tradesigx.db'

engine = create_engine(f'sqlite:///{db_path}', connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)

def init_db(force_create=True):
    """
    Returns a DBManager instance.
    Ensures all tables exist by calling create_all(engine).
    """
    Base.metadata.create_all(engine)
    db = DBManager()
    return db

def seed_plans():
    """Seed the database with default subscription plans"""
    db = DBManager()
    if not db.session.query(SubscriptionPlan).first():
        plans = [
            SubscriptionPlan(name="free", display_name="Free", price_usd=0, signals_per_day=3, 
                           features='{"delay": "15min", "radar": false, "support": "community"}'),
            SubscriptionPlan(name="basic", display_name="Basic", price_usd=9.99, signals_per_day=15, 
                           features='{"delay": "realtime", "radar": false, "support": "email"}'),
            SubscriptionPlan(name="pro", display_name="Pro", price_usd=29.99, signals_per_day=-1, 
                           features='{"delay": "realtime", "radar": true, "support": "priority"}'),
            SubscriptionPlan(name="vip", display_name="VIP", price_usd=99.99, signals_per_day=-1, 
                           features='{"delay": "realtime", "radar": true, "support": "dedicated", "tailored_support": true, "early_access": true}'),
        ]
        for plan in plans:
            db.session.add(plan)
        db.session.commit()
    db.close()

class DBManager:
    def __init__(self):
        self.session = Session()

    def get_user_by_telegram_id(self, telegram_id):
        return self.session.query(User).filter(User.telegram_id == telegram_id).first()

    def get_all_users(self):
        return self.session.query(User).all()
    
    def get_users_paginated(self, page=1, per_page=10):
        return self.session.query(User).offset((page-1)*per_page).limit(per_page).all()
    
    def get_user_count(self):
        return self.session.query(User).count()
    
    def get_pending_kyc(self):
        return self.session.query(User).filter(User.kyc_status == "pending").all()
    
    def get_subscription_plan(self, plan_name):
        return self.session.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_name).first()
    
    def get_all_plans(self):
        return self.session.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    
    def create_payment(self, user_id, amount, method, plan, ref):
        payment = PaymentTransaction(
            user_id=user_id, amount=amount, payment_method=method,
            plan_purchased=plan, transaction_ref=ref
        )
        self.session.add(payment)
        self.session.commit()
        return payment
    
    def get_payment_by_ref(self, ref):
        return self.session.query(PaymentTransaction).filter(PaymentTransaction.transaction_ref == ref).first()

    def add(self, obj):
        self.session.add(obj)

    def commit(self):
        self.session.commit()

    def close(self):
        self.session.close()
