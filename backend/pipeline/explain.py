import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from ..schemas import FeatureVector, ScoreResult

logger = logging.getLogger(__name__)

class ExplanationEngine:
    def __init__(self):
        self.feature_names = [
            'amount', 'amount_z_score', 'amount_log', 'amount_rolling_mean_1h', 'amount_rolling_std_1h',
            'amount_rolling_mean_24h', 'amount_rolling_std_24h', 'txn_count_5m', 'txn_count_1h', 'txn_count_24h',
            'distinct_merchants_5m', 'distinct_merchants_1h', 'distinct_merchants_24h', 'distance_from_home',
            'speed_from_last_txn', 'country_change', 'city_change', 'hour_of_day', 'day_of_week',
            'is_holiday', 'is_weekend', 'merchant_fraud_rate', 'mcc_fraud_rate', 'merchant_txn_count',
            'device_rarity_score', 'ip_rarity_score', 'device_change', 'ip_change', 'channel_card_present',
            'channel_web', 'channel_app', 'merchant_id_encoded', 'mcc_encoded', 'country_encoded'
        ]

    async def generate_explanation(self, features: FeatureVector, score_result: ScoreResult) -> Dict[str, Any]:
        """Generate comprehensive explanation for fraud score"""
        try:
            # Feature importance analysis
            feature_importance = self._calculate_feature_importance(features)
            
            # Counterfactual analysis
            counterfactuals = self._generate_counterfactuals(features, score_result)
            
            # Risk factor analysis
            risk_factors = self._analyze_risk_factors(features)
            
            # Timeline analysis
            timeline_analysis = self._analyze_timeline_patterns(features)
            
            return {
                "score_breakdown": {
                    "ensemble_score": score_result.score,
                    "threshold": score_result.threshold,
                    "is_alert": score_result.is_alert,
                    "confidence": score_result.confidence
                },
                "feature_importance": feature_importance,
                "counterfactuals": counterfactuals,
                "risk_factors": risk_factors,
                "timeline_analysis": timeline_analysis,
                "recommendations": self._generate_recommendations(features, score_result)
            }
            
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return {
                "error": "Failed to generate explanation",
                "score": score_result.score,
                "is_alert": score_result.is_alert
            }

    def _calculate_feature_importance(self, features: FeatureVector) -> List[Dict[str, Any]]:
        """Calculate feature importance based on deviation from normal patterns"""
        feature_values = self._features_to_dict(features)
        
        # Define normal ranges for each feature
        normal_ranges = {
            'amount_z_score': (-2, 2),
            'txn_count_1h': (0, 5),
            'txn_count_24h': (0, 20),
            'distance_from_home': (0, 50),
            'merchant_fraud_rate': (0, 0.05),
            'device_rarity_score': (0, 0.5),
            'ip_rarity_score': (0, 0.5),
            'amount_rolling_std_1h': (0, 100),
            'speed_from_last_txn': (0, 500)
        }
        
        importance_scores = []
        
        for feature_name, value in feature_values.items():
            if feature_name in normal_ranges:
                min_val, max_val = normal_ranges[feature_name]
                
                # Calculate deviation from normal range
                if value < min_val:
                    deviation = abs(value - min_val) / abs(min_val) if min_val != 0 else 1.0
                elif value > max_val:
                    deviation = abs(value - max_val) / abs(max_val) if max_val != 0 else 1.0
                else:
                    deviation = 0.0
                
                # Normalize deviation to 0-1 range
                normalized_deviation = min(1.0, deviation)
                
                importance_scores.append({
                    "feature": feature_name,
                    "value": value,
                    "normal_range": normal_ranges[feature_name],
                    "deviation": normalized_deviation,
                    "contribution": normalized_deviation * 100
                })
        
        # Sort by contribution
        importance_scores.sort(key=lambda x: x["contribution"], reverse=True)
        return importance_scores[:10]  # Top 10 features

    def _generate_counterfactuals(self, features: FeatureVector, score_result: ScoreResult) -> List[Dict[str, Any]]:
        """Generate counterfactual explanations"""
        counterfactuals = []
        
        # Amount-based counterfactuals
        if features.amount_z_score > 2.0:
            suggested_amount = features.amount * 0.5  # Reduce by 50%
            counterfactuals.append({
                "type": "amount_reduction",
                "description": f"Reduce transaction amount from ${features.amount:.2f} to ${suggested_amount:.2f}",
                "expected_impact": "High",
                "reasoning": "Amount is significantly higher than customer's normal pattern"
            })
        
        # Velocity-based counterfactuals
        if features.txn_count_1h > 5:
            counterfactuals.append({
                "type": "velocity_reduction",
                "description": "Wait before making additional transactions",
                "expected_impact": "Medium",
                "reasoning": "Transaction frequency is unusually high"
            })
        
        # Geographic counterfactuals
        if features.country_change:
            counterfactuals.append({
                "type": "geographic_consistency",
                "description": "Use card in home country or notify bank of travel",
                "expected_impact": "High",
                "reasoning": "Transaction location differs from customer's usual pattern"
            })
        
        # Merchant-based counterfactuals
        if features.merchant_fraud_rate > 0.1:
            counterfactuals.append({
                "type": "merchant_selection",
                "description": "Use a different merchant or payment method",
                "expected_impact": "Medium",
                "reasoning": "Merchant has high historical fraud rate"
            })
        
        # Device-based counterfactuals
        if features.device_rarity_score > 0.8:
            counterfactuals.append({
                "type": "device_verification",
                "description": "Use a previously used device or verify device",
                "expected_impact": "Medium",
                "reasoning": "Device is rarely used by this customer"
            })
        
        return counterfactuals

    def _analyze_risk_factors(self, features: FeatureVector) -> Dict[str, Any]:
        """Analyze risk factors in the transaction"""
        risk_factors = {
            "high_risk": [],
            "medium_risk": [],
            "low_risk": []
        }
        
        # High risk factors
        if features.amount_z_score > 3.0:
            risk_factors["high_risk"].append({
                "factor": "Extreme amount deviation",
                "value": features.amount_z_score,
                "threshold": 3.0
            })
        
        if features.country_change:
            risk_factors["high_risk"].append({
                "factor": "Country change",
                "value": "True",
                "threshold": "False"
            })
        
        if features.txn_count_1h > 10:
            risk_factors["high_risk"].append({
                "factor": "Very high transaction velocity",
                "value": features.txn_count_1h,
                "threshold": 10
            })
        
        # Medium risk factors
        if features.amount_z_score > 2.0:
            risk_factors["medium_risk"].append({
                "factor": "High amount deviation",
                "value": features.amount_z_score,
                "threshold": 2.0
            })
        
        if features.merchant_fraud_rate > 0.05:
            risk_factors["medium_risk"].append({
                "factor": "Suspicious merchant",
                "value": features.merchant_fraud_rate,
                "threshold": 0.05
            })
        
        if features.device_rarity_score > 0.7:
            risk_factors["medium_risk"].append({
                "factor": "Unusual device",
                "value": features.device_rarity_score,
                "threshold": 0.7
            })
        
        # Low risk factors
        if features.hour_of_day < 6 or features.hour_of_day > 22:
            risk_factors["low_risk"].append({
                "factor": "Unusual hour",
                "value": features.hour_of_day,
                "threshold": "6-22"
            })
        
        if features.is_weekend:
            risk_factors["low_risk"].append({
                "factor": "Weekend transaction",
                "value": "True",
                "threshold": "False"
            })
        
        return risk_factors

    def _analyze_timeline_patterns(self, features: FeatureVector) -> Dict[str, Any]:
        """Analyze temporal patterns in the transaction"""
        timeline_analysis = {
            "hour_analysis": self._analyze_hour_pattern(features.hour_of_day),
            "day_analysis": self._analyze_day_pattern(features.day_of_week),
            "velocity_analysis": self._analyze_velocity_pattern(features),
            "seasonal_analysis": self._analyze_seasonal_pattern(features)
        }
        
        return timeline_analysis

    def _analyze_hour_pattern(self, hour: int) -> Dict[str, Any]:
        """Analyze hour-of-day pattern"""
        if 6 <= hour <= 22:
            risk_level = "Low"
            reasoning = "Normal business hours"
        elif 22 <= hour <= 23 or 0 <= hour <= 5:
            risk_level = "Medium"
            reasoning = "Late night/early morning hours"
        else:
            risk_level = "High"
            reasoning = "Unusual hour"
        
        return {
            "hour": hour,
            "risk_level": risk_level,
            "reasoning": reasoning,
            "is_usual": 6 <= hour <= 22
        }

    def _analyze_day_pattern(self, day: int) -> Dict[str, Any]:
        """Analyze day-of-week pattern"""
        if day < 5:  # Monday to Friday
            risk_level = "Low"
            reasoning = "Weekday transaction"
        else:  # Weekend
            risk_level = "Medium"
            reasoning = "Weekend transaction"
        
        return {
            "day": day,
            "day_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day],
            "risk_level": risk_level,
            "reasoning": reasoning,
            "is_weekend": day >= 5
        }

    def _analyze_velocity_pattern(self, features: FeatureVector) -> Dict[str, Any]:
        """Analyze transaction velocity patterns"""
        velocity_analysis = {
            "short_term": {
                "txn_count_5m": features.txn_count_5m,
                "risk_level": "High" if features.txn_count_5m > 3 else "Medium" if features.txn_count_5m > 1 else "Low"
            },
            "medium_term": {
                "txn_count_1h": features.txn_count_1h,
                "risk_level": "High" if features.txn_count_1h > 8 else "Medium" if features.txn_count_1h > 3 else "Low"
            },
            "long_term": {
                "txn_count_24h": features.txn_count_24h,
                "risk_level": "High" if features.txn_count_24h > 30 else "Medium" if features.txn_count_24h > 15 else "Low"
            }
        }
        
        return velocity_analysis

    def _analyze_seasonal_pattern(self, features: FeatureVector) -> Dict[str, Any]:
        """Analyze seasonal patterns"""
        return {
            "is_holiday": features.is_holiday,
            "is_weekend": features.is_weekend,
            "risk_level": "Medium" if features.is_holiday else "Low",
            "reasoning": "Holiday transactions may have different patterns"
        }

    def _generate_recommendations(self, features: FeatureVector, score_result: ScoreResult) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if score_result.is_alert:
            recommendations.append("Review this transaction manually")
            recommendations.append("Contact customer for verification if necessary")
        
        if features.amount_z_score > 2.0:
            recommendations.append("Consider amount-based limits for this customer")
        
        if features.txn_count_1h > 5:
            recommendations.append("Implement velocity-based restrictions")
        
        if features.country_change:
            recommendations.append("Enable travel notifications for this customer")
        
        if features.merchant_fraud_rate > 0.1:
            recommendations.append("Monitor transactions with this merchant category")
        
        if not recommendations:
            recommendations.append("Transaction appears normal - continue monitoring")
        
        return recommendations

    def _features_to_dict(self, features: FeatureVector) -> Dict[str, float]:
        """Convert FeatureVector to dictionary"""
        return {
            'amount': features.amount,
            'amount_z_score': features.amount_z_score,
            'amount_log': features.amount_log,
            'amount_rolling_mean_1h': features.amount_rolling_mean_1h,
            'amount_rolling_std_1h': features.amount_rolling_std_1h,
            'amount_rolling_mean_24h': features.amount_rolling_mean_24h,
            'amount_rolling_std_24h': features.amount_rolling_std_24h,
            'txn_count_5m': features.txn_count_5m,
            'txn_count_1h': features.txn_count_1h,
            'txn_count_24h': features.txn_count_24h,
            'distinct_merchants_5m': features.distinct_merchants_5m,
            'distinct_merchants_1h': features.distinct_merchants_1h,
            'distinct_merchants_24h': features.distinct_merchants_24h,
            'distance_from_home': features.distance_from_home,
            'speed_from_last_txn': features.speed_from_last_txn or 0,
            'country_change': float(features.country_change),
            'city_change': float(features.city_change),
            'hour_of_day': features.hour_of_day,
            'day_of_week': features.day_of_week,
            'is_holiday': float(features.is_holiday),
            'is_weekend': float(features.is_weekend),
            'merchant_fraud_rate': features.merchant_fraud_rate,
            'mcc_fraud_rate': features.mcc_fraud_rate,
            'merchant_txn_count': features.merchant_txn_count,
            'device_rarity_score': features.device_rarity_score,
            'ip_rarity_score': features.ip_rarity_score,
            'device_change': float(features.device_change),
            'ip_change': float(features.ip_change),
            'channel_card_present': float(features.channel_card_present),
            'channel_web': float(features.channel_web),
            'channel_app': float(features.channel_app),
            'merchant_id_encoded': features.merchant_id_encoded,
            'mcc_encoded': features.mcc_encoded,
            'country_encoded': features.country_encoded
        }
