import numpy as np
import pandas as pd
from typing import Dict, Any, List
import joblib
import torch
import torch.nn as nn
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import logging
import os
from datetime import datetime

from ..schemas import FeatureVector, ScoreResult

logger = logging.getLogger(__name__)

class Autoencoder(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, latent_dim: int = 16):
        super(Autoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim)
        )
    
    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded
    
    def encode(self, x):
        return self.encoder(x)

class FraudDetector:
    def __init__(self):
        self.isolation_forest = None
        self.autoencoder = None
        self.scaler = None
        self.threshold = 0.95  # 95th percentile for anomaly detection
        self.feature_columns = None
        self.model_loaded = False

    async def load_models(self):
        """Load trained models from disk or train new ones"""
        try:
            model_path = "data/artifacts"
            os.makedirs(model_path, exist_ok=True)
            
            # Try to load existing models
            if os.path.exists(f"{model_path}/isolation_forest.joblib"):
                self.isolation_forest = joblib.load(f"{model_path}/isolation_forest.joblib")
                logger.info("Loaded existing Isolation Forest model")
            else:
                await self._train_isolation_forest()
            
            if os.path.exists(f"{model_path}/autoencoder.pth"):
                self.autoencoder = torch.load(f"{model_path}/autoencoder.pth")
                self.autoencoder.eval()
                logger.info("Loaded existing Autoencoder model")
            else:
                await self._train_autoencoder()
            
            if os.path.exists(f"{model_path}/scaler.joblib"):
                self.scaler = joblib.load(f"{model_path}/scaler.joblib")
                logger.info("Loaded existing scaler")
            else:
                self.scaler = StandardScaler()
            
            self.model_loaded = True
            logger.info("All models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            # Train new models if loading fails
            await self._train_models()

    async def _train_models(self):
        """Train new models with synthetic data"""
        logger.info("Training new models with synthetic data")
        await self._train_isolation_forest()
        await self._train_autoencoder()

    async def _train_isolation_forest(self):
        """Train Isolation Forest model"""
        try:
            # Generate synthetic training data
            n_samples = 10000
            synthetic_data = self._generate_synthetic_data(n_samples)
            
            # Train Isolation Forest
            self.isolation_forest = IsolationForest(
                contamination=0.1,
                n_estimators=100,
                random_state=42
            )
            self.isolation_forest.fit(synthetic_data)
            
            # Save model
            model_path = "data/artifacts"
            os.makedirs(model_path, exist_ok=True)
            joblib.dump(self.isolation_forest, f"{model_path}/isolation_forest.joblib")
            
            logger.info("Isolation Forest trained and saved")
            
        except Exception as e:
            logger.error(f"Error training Isolation Forest: {e}")
            # Create a simple fallback model
            self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)

    async def _train_autoencoder(self):
        """Train Autoencoder model"""
        try:
            # Generate synthetic training data
            n_samples = 10000
            synthetic_data = self._generate_synthetic_data(n_samples)
            
            # Normalize data
            self.scaler = StandardScaler()
            normalized_data = self.scaler.fit_transform(synthetic_data)
            
            # Train Autoencoder
            input_dim = synthetic_data.shape[1]
            self.autoencoder = Autoencoder(input_dim=input_dim, hidden_dim=64, latent_dim=16)
            
            # Training parameters
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(self.autoencoder.parameters(), lr=0.001)
            
            # Convert to tensor
            X = torch.FloatTensor(normalized_data)
            
            # Training loop
            self.autoencoder.train()
            for epoch in range(50):
                optimizer.zero_grad()
                outputs = self.autoencoder(X)
                loss = criterion(outputs, X)
                loss.backward()
                optimizer.step()
                
                if epoch % 10 == 0:
                    logger.info(f"Autoencoder epoch {epoch}, loss: {loss.item():.4f}")
            
            # Save model and scaler
            model_path = "data/artifacts"
            os.makedirs(model_path, exist_ok=True)
            torch.save(self.autoencoder, f"{model_path}/autoencoder.pth")
            joblib.dump(self.scaler, f"{model_path}/scaler.joblib")
            
            logger.info("Autoencoder trained and saved")
            
        except Exception as e:
            logger.error(f"Error training Autoencoder: {e}")
            # Create a simple fallback model
            input_dim = 35  # Number of features
            self.autoencoder = Autoencoder(input_dim=input_dim)
            self.scaler = StandardScaler()

    def _generate_synthetic_data(self, n_samples: int) -> np.ndarray:
        """Generate synthetic transaction data for training"""
        np.random.seed(42)
        
        # Generate realistic synthetic features
        data = []
        for _ in range(n_samples):
            # Amount features
            amount = np.random.lognormal(4, 1)  # Log-normal distribution
            amount_z_score = np.random.normal(0, 1)
            amount_log = np.log(amount + 1)
            amount_rolling_mean_1h = amount * np.random.uniform(0.8, 1.2)
            amount_rolling_std_1h = amount * np.random.uniform(0.1, 0.3)
            amount_rolling_mean_24h = amount * np.random.uniform(0.9, 1.1)
            amount_rolling_std_24h = amount * np.random.uniform(0.2, 0.4)
            
            # Velocity features
            txn_count_5m = np.random.poisson(1)
            txn_count_1h = np.random.poisson(3)
            txn_count_24h = np.random.poisson(20)
            distinct_merchants_5m = np.random.poisson(1)
            distinct_merchants_1h = np.random.poisson(2)
            distinct_merchants_24h = np.random.poisson(8)
            
            # Geographic features
            distance_from_home = np.random.exponential(50)  # Exponential distribution
            speed_from_last_txn = np.random.exponential(100) if np.random.random() > 0.5 else 0
            country_change = np.random.choice([0, 1], p=[0.95, 0.05])
            city_change = np.random.choice([0, 1], p=[0.9, 0.1])
            
            # Time features
            hour_of_day = np.random.randint(0, 24)
            day_of_week = np.random.randint(0, 7)
            is_holiday = np.random.choice([0, 1], p=[0.95, 0.05])
            is_weekend = np.random.choice([0, 1], p=[0.7, 0.3])
            
            # Merchant features
            merchant_fraud_rate = np.random.beta(1, 99)  # Beta distribution, mostly low fraud
            mcc_fraud_rate = np.random.beta(1, 99)
            merchant_txn_count = np.random.poisson(100)
            
            # Device features
            device_rarity_score = np.random.uniform(0, 1)
            ip_rarity_score = np.random.uniform(0, 1)
            device_change = np.random.choice([0, 1], p=[0.9, 0.1])
            ip_change = np.random.choice([0, 1], p=[0.85, 0.15])
            
            # Channel features
            channel_card_present = np.random.choice([0, 1], p=[0.6, 0.4])
            channel_web = np.random.choice([0, 1], p=[0.3, 0.7])
            channel_app = np.random.choice([0, 1], p=[0.1, 0.9])
            
            # Encoding features
            merchant_id_encoded = np.random.uniform(0, 1)
            mcc_encoded = np.random.uniform(0, 1)
            country_encoded = np.random.uniform(0, 1)
            
            # Combine all features
            features = [
                amount, amount_z_score, amount_log, amount_rolling_mean_1h, amount_rolling_std_1h,
                amount_rolling_mean_24h, amount_rolling_std_24h, txn_count_5m, txn_count_1h, txn_count_24h,
                distinct_merchants_5m, distinct_merchants_1h, distinct_merchants_24h, distance_from_home,
                speed_from_last_txn or 0, country_change, city_change, hour_of_day, day_of_week,
                is_holiday, is_weekend, merchant_fraud_rate, mcc_fraud_rate, merchant_txn_count,
                device_rarity_score, ip_rarity_score, device_change, ip_change, channel_card_present,
                channel_web, channel_app, merchant_id_encoded, mcc_encoded, country_encoded
            ]
            
            data.append(features)
        
        return np.array(data)

    async def score(self, features: FeatureVector) -> ScoreResult:
        """Score a transaction for fraud risk"""
        try:
            if not self.model_loaded:
                await self.load_models()
            
            # Convert features to array
            feature_array = self._features_to_array(features)
            
            # Get scores from both models
            if_score = await self._isolation_forest_score(feature_array)
            ae_score = await self._autoencoder_score(feature_array)
            
            # Ensemble score (weighted average)
            ensemble_score = 0.4 * if_score + 0.6 * ae_score
            
            # Determine threshold and alert
            threshold = self.threshold
            is_alert = ensemble_score > threshold
            
            # Generate explanation
            explanation = self._generate_explanation(features, ensemble_score, if_score, ae_score)
            
            return ScoreResult(
                score=float(ensemble_score),
                threshold=threshold,
                is_alert=is_alert,
                model_used="ensemble",
                explanation=explanation,
                confidence=min(ensemble_score * 1.2, 1.0)  # Confidence based on score
            )
            
        except Exception as e:
            logger.error(f"Error scoring transaction: {e}")
            # Return default score on error
            return ScoreResult(
                score=0.5,
                threshold=self.threshold,
                is_alert=False,
                model_used="fallback",
                explanation={"error": "Model scoring failed"},
                confidence=0.0
            )

    def _features_to_array(self, features: FeatureVector) -> np.ndarray:
        """Convert FeatureVector to numpy array"""
        return np.array([
            features.amount, features.amount_z_score, features.amount_log,
            features.amount_rolling_mean_1h, features.amount_rolling_std_1h,
            features.amount_rolling_mean_24h, features.amount_rolling_std_24h,
            features.txn_count_5m, features.txn_count_1h, features.txn_count_24h,
            features.distinct_merchants_5m, features.distinct_merchants_1h, features.distinct_merchants_24h,
            features.distance_from_home, features.speed_from_last_txn or 0,
            features.country_change, features.city_change, features.hour_of_day,
            features.day_of_week, features.is_holiday, features.is_weekend,
            features.merchant_fraud_rate, features.mcc_fraud_rate, features.merchant_txn_count,
            features.device_rarity_score, features.ip_rarity_score,
            features.device_change, features.ip_change, features.channel_card_present,
            features.channel_web, features.channel_app, features.merchant_id_encoded,
            features.mcc_encoded, features.country_encoded
        ]).reshape(1, -1)

    async def _isolation_forest_score(self, feature_array: np.ndarray) -> float:
        """Get Isolation Forest anomaly score"""
        try:
            if self.isolation_forest is None:
                return 0.5
            
            # Isolation Forest returns negative scores for anomalies
            # Convert to positive scores (higher = more anomalous)
            score = -self.isolation_forest.score_samples(feature_array)[0]
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.error(f"Error in Isolation Forest scoring: {e}")
            return 0.5

    async def _autoencoder_score(self, feature_array: np.ndarray) -> float:
        """Get Autoencoder reconstruction error score"""
        try:
            if self.autoencoder is None or self.scaler is None:
                return 0.5
            
            # Normalize features
            normalized_features = self.scaler.transform(feature_array)
            
            # Get reconstruction error
            with torch.no_grad():
                X = torch.FloatTensor(normalized_features)
                reconstructed = self.autoencoder(X)
                mse = nn.MSELoss()(reconstructed, X)
                score = mse.item()
            
            # Normalize score to [0, 1] range
            # Higher reconstruction error = more anomalous
            normalized_score = min(1.0, score * 10)  # Scale factor for normalization
            return normalized_score
            
        except Exception as e:
            logger.error(f"Error in Autoencoder scoring: {e}")
            return 0.5

    def _generate_explanation(self, features: FeatureVector, ensemble_score: float, 
                            if_score: float, ae_score: float) -> Dict[str, Any]:
        """Generate explanation for the fraud score"""
        # Top contributing features
        feature_contributions = {
            "amount_z_score": abs(features.amount_z_score),
            "txn_count_1h": features.txn_count_1h / 10.0,  # Normalize
            "distance_from_home": features.distance_from_home / 100.0,  # Normalize
            "merchant_fraud_rate": features.merchant_fraud_rate,
            "device_rarity_score": features.device_rarity_score,
            "country_change": 1.0 if features.country_change else 0.0
        }
        
        # Sort by contribution
        sorted_features = sorted(feature_contributions.items(), key=lambda x: x[1], reverse=True)
        top_features = sorted_features[:3]
        
        # Generate counterfactual suggestions
        counterfactuals = []
        if features.amount_z_score > 2.0:
            counterfactuals.append("Reduce transaction amount")
        if features.txn_count_1h > 5:
            counterfactuals.append("Reduce transaction frequency")
        if features.country_change:
            counterfactuals.append("Use card in home country")
        
        return {
            "ensemble_score": ensemble_score,
            "isolation_forest_score": if_score,
            "autoencoder_score": ae_score,
            "top_contributing_features": top_features,
            "counterfactuals": counterfactuals,
            "risk_factors": {
                "high_amount": features.amount_z_score > 2.0,
                "high_velocity": features.txn_count_1h > 5,
                "geographic_anomaly": features.country_change,
                "suspicious_merchant": features.merchant_fraud_rate > 0.1,
                "device_anomaly": features.device_rarity_score > 0.8
            }
        }

    async def health_check(self) -> bool:
        """Check if models are loaded and ready"""
        return self.model_loaded and self.isolation_forest is not None and self.autoencoder is not None
