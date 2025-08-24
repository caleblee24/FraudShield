from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ChannelType(str, Enum):
    CARD_PRESENT = "card_present"
    WEB = "web"
    APP = "app"
    PHONE = "phone"

class SimulationScenario(str, Enum):
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    HIGH_AMOUNT = "high_amount"
    VELOCITY_ATTACK = "velocity_attack"
    CARD_NOT_PRESENT = "card_not_present"
    MERCHANT_TRIANGULATION = "merchant_triangulation"

class AlertStatus(str, Enum):
    NEW = "new"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"

# Base transaction model
class Transaction(BaseModel):
    txn_id: str
    ts: datetime
    amount: float = Field(..., gt=0)
    merchant_cat: str
    merchant_id: str
    mcc: str
    currency: str = Field(default="USD", max_length=3)
    country: str
    city: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    channel: ChannelType
    card_id: str
    customer_id: str
    device_id: Optional[str] = None
    ip: Optional[str] = None
    is_fraud: Optional[bool] = None

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

    @validator('lat')
    def validate_lat(cls, v):
        if v is not None and (v < -90 or v > 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @validator('lon')
    def validate_lon(cls, v):
        if v is not None and (v < -180 or v > 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v

# API request/response models
class ScoreRequest(BaseModel):
    amount: float = Field(..., gt=0)
    merchant_cat: str
    merchant_id: str
    mcc: str
    currency: str = Field(default="USD", max_length=3)
    country: str
    city: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    channel: ChannelType
    card_id: str
    customer_id: str
    device_id: Optional[str] = None
    ip: Optional[str] = None

class ScoreResponse(BaseModel):
    txn_id: str
    score: float = Field(..., ge=0, le=1)
    threshold: float = Field(..., ge=0, le=1)
    is_alert: bool
    model_used: str
    explanation: Dict[str, Any]

class TransactionResponse(BaseModel):
    txn_id: str
    ts: datetime
    amount: float
    merchant_cat: str
    merchant_id: str
    score: float
    is_alert: bool
    status: str

class Alert(BaseModel):
    alert_id: str
    txn_id: str
    score: float
    timestamp: datetime
    status: AlertStatus
    explanation: Dict[str, Any]
    analyst_notes: Optional[str] = None
    resolution: Optional[str] = None

class AlertList(BaseModel):
    alerts: List[Alert]
    total: int
    limit: int
    offset: int

class SimulationRequest(BaseModel):
    scenario: SimulationScenario
    customer_id: Optional[str] = None
    card_id: Optional[str] = None
    amount: Optional[float] = None
    merchant_id: Optional[str] = None

# Feature engineering models
class FeatureVector(BaseModel):
    # Amount features
    amount: float
    amount_z_score: float
    amount_log: float
    amount_rolling_mean_1h: float
    amount_rolling_std_1h: float
    amount_rolling_mean_24h: float
    amount_rolling_std_24h: float
    
    # Velocity features
    txn_count_5m: int
    txn_count_1h: int
    txn_count_24h: int
    distinct_merchants_5m: int
    distinct_merchants_1h: int
    distinct_merchants_24h: int
    
    # Geographic features
    distance_from_home: float
    speed_from_last_txn: Optional[float] = None
    country_change: bool
    city_change: bool
    
    # Time features
    hour_of_day: int
    day_of_week: int
    is_holiday: bool
    is_weekend: bool
    
    # Merchant features
    merchant_fraud_rate: float
    mcc_fraud_rate: float
    merchant_txn_count: int
    
    # Device/IP features
    device_rarity_score: float
    ip_rarity_score: float
    device_change: bool
    ip_change: bool
    
    # Channel features
    channel_card_present: bool
    channel_web: bool
    channel_app: bool
    
    # Categorical encodings
    merchant_id_encoded: float
    mcc_encoded: float
    country_encoded: float

class ScoreResult(BaseModel):
    score: float = Field(..., ge=0, le=1)
    threshold: float = Field(..., ge=0, le=1)
    is_alert: bool
    model_used: str
    explanation: Dict[str, Any]
    confidence: float = Field(..., ge=0, le=1)

# Model metadata
class ModelMetadata(BaseModel):
    model_id: str
    model_type: str
    version: str
    created_at: datetime
    performance_metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    threshold: float

# Monitoring models
class SystemMetrics(BaseModel):
    timestamp: datetime
    requests_per_second: float
    average_latency_ms: float
    p95_latency_ms: float
    alert_rate: float
    model_accuracy: Optional[float] = None
    active_alerts: int
    total_transactions: int

class DriftMetrics(BaseModel):
    timestamp: datetime
    feature_drift_scores: Dict[str, float]
    data_quality_score: float
    concept_drift_detected: bool
    drift_severity: str

# Configuration models
class ModelConfig(BaseModel):
    isolation_forest_contamination: float = 0.1
    isolation_forest_n_estimators: int = 100
    autoencoder_hidden_dim: int = 64
    autoencoder_latent_dim: int = 16
    threshold_percentile: float = 95.0
    ensemble_weights: Dict[str, float] = {
        "isolation_forest": 0.4,
        "autoencoder": 0.6
    }

class FeatureConfig(BaseModel):
    rolling_windows: List[str] = ["5m", "1h", "24h", "7d"]
    geo_features_enabled: bool = True
    velocity_features_enabled: bool = True
    merchant_features_enabled: bool = True
    device_features_enabled: bool = True
    time_features_enabled: bool = True
