from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from .schemas import (
    Transaction, TransactionResponse, Alert, SimulationRequest,
    ScoreRequest, ScoreResponse, AlertList
)
from .pipeline.model_infer import FraudDetector
from .pipeline.feature_engineering import FeatureEngineer
from .utils.db import get_db, DatabaseManager
from .utils.kafka import KafkaProducer, KafkaConsumer
from .pipeline.explain import ExplanationEngine

# Prometheus metrics
REQUEST_COUNT = Counter('fraud_detector_requests_total', 'Total requests', ['endpoint'])
REQUEST_LATENCY = Histogram('fraud_detector_request_duration_seconds', 'Request latency', ['endpoint'])
SCORE_DISTRIBUTION = Histogram('fraud_detector_score_distribution', 'Fraud score distribution')
ALERT_COUNT = Counter('fraud_detector_alerts_total', 'Total alerts generated')

app = FastAPI(
    title="FraudShield API",
    description="Real-time financial fraud detection system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
fraud_detector = FraudDetector()
feature_engineer = FeatureEngineer()
kafka_producer = KafkaProducer()
explanation_engine = ExplanationEngine()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await fraud_detector.load_models()
    await kafka_producer.connect()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await kafka_producer.close()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "FraudShield API is running", "version": "1.0.0"}

@app.post("/score", response_model=ScoreResponse)
async def score_transaction(
    request: ScoreRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_db)
):
    """Score a transaction for fraud risk"""
    start_time = time.time()
    REQUEST_COUNT.labels(endpoint='/score').inc()
    
    try:
        # Create transaction record
        transaction = Transaction(
            txn_id=str(uuid.uuid4()),
            ts=datetime.utcnow(),
            amount=request.amount,
            merchant_cat=request.merchant_cat,
            merchant_id=request.merchant_id,
            mcc=request.mcc,
            currency=request.currency,
            country=request.country,
            city=request.city,
            lat=request.lat,
            lon=request.lon,
            channel=request.channel,
            card_id=request.card_id,
            customer_id=request.customer_id,
            device_id=request.device_id,
            ip=request.ip
        )
        
        # Engineer features
        features = await feature_engineer.engineer_features(transaction, db)
        
        # Get fraud score
        score_result = await fraud_detector.score(features)
        
        # Record metrics
        SCORE_DISTRIBUTION.observe(score_result.score)
        
        # Create response
        response = ScoreResponse(
            txn_id=transaction.txn_id,
            score=score_result.score,
            threshold=score_result.threshold,
            is_alert=score_result.is_alert,
            model_used=score_result.model_used,
            explanation=score_result.explanation
        )
        
        # Store transaction and score in database
        await db.store_transaction(transaction, features, score_result)
        
        # Send to Kafka for real-time processing
        background_tasks.add_task(
            kafka_producer.send_transaction,
            "transactions.raw",
            transaction.dict()
        )
        
        # Generate alert if score exceeds threshold
        if score_result.is_alert:
            ALERT_COUNT.inc()
            alert = Alert(
                alert_id=str(uuid.uuid4()),
                txn_id=transaction.txn_id,
                score=score_result.score,
                timestamp=datetime.utcnow(),
                status="new",
                explanation=score_result.explanation
            )
            await db.store_alert(alert)
            
            # Send alert to Kafka
            background_tasks.add_task(
                kafka_producer.send_transaction,
                "alerts.suspicious",
                alert.dict()
            )
        
        # Record latency
        latency = time.time() - start_time
        REQUEST_LATENCY.labels(endpoint='/score').observe(latency)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

@app.get("/alerts", response_model=AlertList)
async def get_alerts(
    since: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    db: DatabaseManager = Depends(get_db)
):
    """Get alerts with pagination"""
    REQUEST_COUNT.labels(endpoint='/alerts').inc()
    
    if since is None:
        since = datetime.utcnow() - timedelta(hours=24)
    
    alerts = await db.get_alerts(since=since, limit=limit, offset=offset)
    total = await db.get_alert_count(since=since)
    
    return AlertList(
        alerts=alerts,
        total=total,
        limit=limit,
        offset=offset
    )

@app.get("/alerts/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: str,
    db: DatabaseManager = Depends(get_db)
):
    """Get specific alert details"""
    REQUEST_COUNT.labels(endpoint='/alerts/{alert_id}').inc()
    
    alert = await db.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return alert

@app.post("/simulate")
async def simulate_transaction(
    request: SimulationRequest,
    background_tasks: BackgroundTasks
):
    """Simulate a transaction for testing"""
    REQUEST_COUNT.labels(endpoint='/simulate').inc()
    
    try:
        # Generate synthetic transaction based on scenario
        transaction = await generate_synthetic_transaction(request)
        
        # Send to Kafka for processing
        background_tasks.add_task(
            kafka_producer.send_transaction,
            "transactions.raw",
            transaction.dict()
        )
        
        return {
            "message": "Simulation transaction sent",
            "txn_id": transaction.txn_id,
            "scenario": request.scenario
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return JSONResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "healthy",
            "kafka": "healthy",
            "models": "healthy"
        }
    }
    
    # Check database connection
    try:
        db = DatabaseManager()
        await db.health_check()
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Kafka connection
    try:
        await kafka_producer.health_check()
    except Exception as e:
        health_status["services"]["kafka"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check model availability
    try:
        await fraud_detector.health_check()
    except Exception as e:
        health_status["services"]["models"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

async def generate_synthetic_transaction(request: SimulationRequest) -> Transaction:
    """Generate synthetic transaction based on scenario"""
    base_txn = {
        "txn_id": str(uuid.uuid4()),
        "ts": datetime.utcnow(),
        "amount": 100.0,
        "merchant_cat": "retail",
        "merchant_id": "MERCH001",
        "mcc": "5411",
        "currency": "USD",
        "country": "US",
        "city": "New York",
        "lat": 40.7128,
        "lon": -74.0060,
        "channel": "card_present",
        "card_id": "CARD001",
        "customer_id": "CUST001",
        "device_id": "DEVICE001",
        "ip": "192.168.1.1"
    }
    
    if request.scenario == "impossible_travel":
        # Simulate impossible travel - same card used in different countries
        base_txn.update({
            "country": "UK",
            "city": "London",
            "lat": 51.5074,
            "lon": -0.1278,
            "amount": 500.0
        })
    elif request.scenario == "high_amount":
        # Simulate unusually high amount
        base_txn.update({
            "amount": 10000.0,
            "merchant_cat": "electronics"
        })
    elif request.scenario == "velocity_attack":
        # Simulate rapid-fire transactions
        base_txn.update({
            "amount": 50.0,
            "merchant_cat": "gas_station"
        })
    elif request.scenario == "card_not_present":
        # Simulate card-not-present transaction
        base_txn.update({
            "channel": "web",
            "amount": 200.0,
            "merchant_cat": "online_retail"
        })
    
    return Transaction(**base_txn)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
