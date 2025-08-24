import asyncpg
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
from ..schemas import Transaction, FeatureVector, ScoreResult, Alert, AlertStatus

class DatabaseManager:
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL", 
            "postgresql://fraudshield:fraudshield123@localhost:5432/fraudshield"
        )
        self.pool = None

    async def connect(self):
        """Create connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.connection_string)
            await self._create_tables()

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()

    async def _create_tables(self):
        """Create database tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Transactions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    txn_id VARCHAR(36) PRIMARY KEY,
                    ts TIMESTAMP NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    merchant_cat VARCHAR(50) NOT NULL,
                    merchant_id VARCHAR(50) NOT NULL,
                    mcc VARCHAR(10) NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    country VARCHAR(50) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    lat DECIMAL(10,6),
                    lon DECIMAL(10,6),
                    channel VARCHAR(20) NOT NULL,
                    card_id VARCHAR(50) NOT NULL,
                    customer_id VARCHAR(50) NOT NULL,
                    device_id VARCHAR(50),
                    ip VARCHAR(45),
                    is_fraud BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Features table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS features (
                    txn_id VARCHAR(36) PRIMARY KEY REFERENCES transactions(txn_id),
                    amount DECIMAL(10,2) NOT NULL,
                    amount_z_score DECIMAL(10,4),
                    amount_log DECIMAL(10,4),
                    amount_rolling_mean_1h DECIMAL(10,4),
                    amount_rolling_std_1h DECIMAL(10,4),
                    amount_rolling_mean_24h DECIMAL(10,4),
                    amount_rolling_std_24h DECIMAL(10,4),
                    txn_count_5m INTEGER,
                    txn_count_1h INTEGER,
                    txn_count_24h INTEGER,
                    distinct_merchants_5m INTEGER,
                    distinct_merchants_1h INTEGER,
                    distinct_merchants_24h INTEGER,
                    distance_from_home DECIMAL(10,4),
                    speed_from_last_txn DECIMAL(10,4),
                    country_change BOOLEAN,
                    city_change BOOLEAN,
                    hour_of_day INTEGER,
                    day_of_week INTEGER,
                    is_holiday BOOLEAN,
                    is_weekend BOOLEAN,
                    merchant_fraud_rate DECIMAL(10,4),
                    mcc_fraud_rate DECIMAL(10,4),
                    merchant_txn_count INTEGER,
                    device_rarity_score DECIMAL(10,4),
                    ip_rarity_score DECIMAL(10,4),
                    device_change BOOLEAN,
                    ip_change BOOLEAN,
                    channel_card_present BOOLEAN,
                    channel_web BOOLEAN,
                    channel_app BOOLEAN,
                    merchant_id_encoded DECIMAL(10,4),
                    mcc_encoded DECIMAL(10,4),
                    country_encoded DECIMAL(10,4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scores table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    txn_id VARCHAR(36) PRIMARY KEY REFERENCES transactions(txn_id),
                    score DECIMAL(10,4) NOT NULL,
                    threshold DECIMAL(10,4) NOT NULL,
                    is_alert BOOLEAN NOT NULL,
                    model_used VARCHAR(50) NOT NULL,
                    explanation JSONB,
                    confidence DECIMAL(10,4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Alerts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id VARCHAR(36) PRIMARY KEY,
                    txn_id VARCHAR(36) REFERENCES transactions(txn_id),
                    score DECIMAL(10,4) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'new',
                    explanation JSONB,
                    analyst_notes TEXT,
                    resolution TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Model registry table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS model_registry (
                    model_id VARCHAR(50) PRIMARY KEY,
                    model_type VARCHAR(50) NOT NULL,
                    version VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    performance_metrics JSONB,
                    feature_importance JSONB,
                    threshold DECIMAL(10,4),
                    model_path VARCHAR(255),
                    is_active BOOLEAN DEFAULT FALSE
                )
            """)

            # Audit events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(50),
                    action VARCHAR(50) NOT NULL,
                    resource_type VARCHAR(50) NOT NULL,
                    resource_id VARCHAR(50),
                    details JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_customer_id ON transactions(customer_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_ts ON transactions(ts);
                CREATE INDEX IF NOT EXISTS idx_transactions_card_id ON transactions(card_id);
                CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);
                CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score);
            """)

    async def store_transaction(self, transaction: Transaction, features: FeatureVector, score_result: ScoreResult):
        """Store transaction, features, and score in database"""
        async with self.pool.acquire() as conn:
            # Store transaction
            await conn.execute("""
                INSERT INTO transactions (
                    txn_id, ts, amount, merchant_cat, merchant_id, mcc, currency,
                    country, city, lat, lon, channel, card_id, customer_id, device_id, ip, is_fraud
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (txn_id) DO NOTHING
            """, 
                transaction.txn_id, transaction.ts, transaction.amount, transaction.merchant_cat,
                transaction.merchant_id, transaction.mcc, transaction.currency, transaction.country,
                transaction.city, transaction.lat, transaction.lon, transaction.channel,
                transaction.card_id, transaction.customer_id, transaction.device_id, transaction.ip,
                transaction.is_fraud
            )

            # Store features
            await conn.execute("""
                INSERT INTO features (
                    txn_id, amount, amount_z_score, amount_log, amount_rolling_mean_1h,
                    amount_rolling_std_1h, amount_rolling_mean_24h, amount_rolling_std_24h,
                    txn_count_5m, txn_count_1h, txn_count_24h, distinct_merchants_5m,
                    distinct_merchants_1h, distinct_merchants_24h, distance_from_home,
                    speed_from_last_txn, country_change, city_change, hour_of_day,
                    day_of_week, is_holiday, is_weekend, merchant_fraud_rate,
                    mcc_fraud_rate, merchant_txn_count, device_rarity_score,
                    ip_rarity_score, device_change, ip_change, channel_card_present,
                    channel_web, channel_app, merchant_id_encoded, mcc_encoded, country_encoded
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34)
                ON CONFLICT (txn_id) DO NOTHING
            """,
                transaction.txn_id, features.amount, features.amount_z_score, features.amount_log,
                features.amount_rolling_mean_1h, features.amount_rolling_std_1h,
                features.amount_rolling_mean_24h, features.amount_rolling_std_24h,
                features.txn_count_5m, features.txn_count_1h, features.txn_count_24h,
                features.distinct_merchants_5m, features.distinct_merchants_1h,
                features.distinct_merchants_24h, features.distance_from_home,
                features.speed_from_last_txn, features.country_change, features.city_change,
                features.hour_of_day, features.day_of_week, features.is_holiday,
                features.is_weekend, features.merchant_fraud_rate, features.mcc_fraud_rate,
                features.merchant_txn_count, features.device_rarity_score,
                features.ip_rarity_score, features.device_change, features.ip_change,
                features.channel_card_present, features.channel_web, features.channel_app,
                features.merchant_id_encoded, features.mcc_encoded, features.country_encoded
            )

            # Store score
            await conn.execute("""
                INSERT INTO scores (
                    txn_id, score, threshold, is_alert, model_used, explanation, confidence
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (txn_id) DO NOTHING
            """,
                transaction.txn_id, score_result.score, score_result.threshold,
                score_result.is_alert, score_result.model_used,
                json.dumps(score_result.explanation), score_result.confidence
            )

    async def store_alert(self, alert: Alert):
        """Store alert in database"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO alerts (
                    alert_id, txn_id, score, timestamp, status, explanation
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (alert_id) DO NOTHING
            """,
                alert.alert_id, alert.txn_id, alert.score, alert.timestamp,
                alert.status, json.dumps(alert.explanation)
            )

    async def get_alerts(self, since: datetime, limit: int = 100, offset: int = 0) -> List[Alert]:
        """Get alerts with pagination"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT a.alert_id, a.txn_id, a.score, a.timestamp, a.status,
                       a.explanation, a.analyst_notes, a.resolution
                FROM alerts a
                WHERE a.timestamp >= $1
                ORDER BY a.timestamp DESC
                LIMIT $2 OFFSET $3
            """, since, limit, offset)

            return [
                Alert(
                    alert_id=row['alert_id'],
                    txn_id=row['txn_id'],
                    score=float(row['score']),
                    timestamp=row['timestamp'],
                    status=AlertStatus(row['status']),
                    explanation=json.loads(row['explanation']) if row['explanation'] else {},
                    analyst_notes=row['analyst_notes'],
                    resolution=row['resolution']
                )
                for row in rows
            ]

    async def get_alert_count(self, since: datetime) -> int:
        """Get total alert count"""
        async with self.pool.acquire() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM alerts WHERE timestamp >= $1
            """, since)
            return count

    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get specific alert by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT alert_id, txn_id, score, timestamp, status,
                       explanation, analyst_notes, resolution
                FROM alerts WHERE alert_id = $1
            """, alert_id)

            if not row:
                return None

            return Alert(
                alert_id=row['alert_id'],
                txn_id=row['txn_id'],
                score=float(row['score']),
                timestamp=row['timestamp'],
                status=AlertStatus(row['status']),
                explanation=json.loads(row['explanation']) if row['explanation'] else {},
                analyst_notes=row['analyst_notes'],
                resolution=row['resolution']
            )

    async def get_customer_history(self, customer_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get customer transaction history for feature engineering"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT t.txn_id, t.ts, t.amount, t.merchant_id, t.mcc, t.country, t.city,
                       t.lat, t.lon, t.channel, t.device_id, t.ip, s.score
                FROM transactions t
                LEFT JOIN scores s ON t.txn_id = s.txn_id
                WHERE t.customer_id = $1 AND t.ts >= $2
                ORDER BY t.ts DESC
            """, customer_id, datetime.utcnow() - timedelta(hours=hours))

            return [dict(row) for row in rows]

    async def get_merchant_stats(self, merchant_id: str) -> Dict[str, Any]:
        """Get merchant statistics for feature engineering"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_transactions,
                    AVG(amount) as avg_amount,
                    COUNT(CASE WHEN is_fraud = true THEN 1 END) as fraud_count,
                    COUNT(CASE WHEN is_fraud = true THEN 1 END)::float / COUNT(*) as fraud_rate
                FROM transactions 
                WHERE merchant_id = $1
            """, merchant_id)

            return {
                'total_transactions': row['total_transactions'],
                'avg_amount': float(row['avg_amount']) if row['avg_amount'] else 0.0,
                'fraud_count': row['fraud_count'],
                'fraud_rate': float(row['fraud_rate']) if row['fraud_rate'] else 0.0
            }

    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

# Dependency injection
async def get_db() -> DatabaseManager:
    """Get database manager instance"""
    db = DatabaseManager()
    await db.connect()
    return db
