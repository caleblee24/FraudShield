import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import math
from geopy.distance import geodesic
import logging

from ..schemas import Transaction, FeatureVector, ChannelType
from ..utils.db import DatabaseManager

logger = logging.getLogger(__name__)

class FeatureEngineer:
    def __init__(self):
        self.customer_home_locations = {}
        self.merchant_stats_cache = {}

    async def engineer_features(self, transaction: Transaction, db: DatabaseManager) -> FeatureVector:
        """Engineer features for a transaction"""
        try:
            customer_history = await db.get_customer_history(transaction.customer_id, hours=24)
            merchant_stats = await self._get_merchant_stats(transaction.merchant_id, db)
            
            # Calculate features
            amount_features = self._calculate_amount_features(transaction, customer_history)
            velocity_features = self._calculate_velocity_features(transaction, customer_history)
            geo_features = self._calculate_geo_features(transaction, customer_history)
            time_features = self._calculate_time_features(transaction)
            merchant_features = self._calculate_merchant_features(transaction, merchant_stats)
            device_features = self._calculate_device_features(transaction, customer_history)
            channel_features = self._calculate_channel_features(transaction)
            
            return FeatureVector(
                amount=transaction.amount,
                amount_z_score=amount_features['z_score'],
                amount_log=amount_features['log_amount'],
                amount_rolling_mean_1h=amount_features['rolling_mean_1h'],
                amount_rolling_std_1h=amount_features['rolling_std_1h'],
                amount_rolling_mean_24h=amount_features['rolling_mean_24h'],
                amount_rolling_std_24h=amount_features['rolling_std_24h'],
                txn_count_5m=velocity_features['txn_count_5m'],
                txn_count_1h=velocity_features['txn_count_1h'],
                txn_count_24h=velocity_features['txn_count_24h'],
                distinct_merchants_5m=velocity_features['distinct_merchants_5m'],
                distinct_merchants_1h=velocity_features['distinct_merchants_1h'],
                distinct_merchants_24h=velocity_features['distinct_merchants_24h'],
                distance_from_home=geo_features['distance_from_home'],
                speed_from_last_txn=geo_features['speed_from_last_txn'],
                country_change=geo_features['country_change'],
                city_change=geo_features['city_change'],
                hour_of_day=time_features['hour_of_day'],
                day_of_week=time_features['day_of_week'],
                is_holiday=time_features['is_holiday'],
                is_weekend=time_features['is_weekend'],
                merchant_fraud_rate=merchant_features['fraud_rate'],
                mcc_fraud_rate=merchant_features['mcc_fraud_rate'],
                merchant_txn_count=merchant_features['txn_count'],
                device_rarity_score=device_features['device_rarity'],
                ip_rarity_score=device_features['ip_rarity'],
                device_change=device_features['device_change'],
                ip_change=device_features['ip_change'],
                channel_card_present=channel_features['card_present'],
                channel_web=channel_features['web'],
                channel_app=channel_features['app'],
                merchant_id_encoded=hash(transaction.merchant_id) % 1000 / 1000.0,
                mcc_encoded=hash(transaction.mcc) % 1000 / 1000.0,
                country_encoded=hash(transaction.country) % 1000 / 1000.0
            )
        except Exception as e:
            logger.error(f"Error engineering features: {e}")
            return self._get_default_features(transaction)

    def _calculate_amount_features(self, transaction: Transaction, customer_history: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate amount-based features"""
        amounts = [txn['amount'] for txn in customer_history if txn['amount'] > 0]
        
        if not amounts:
            return {
                'z_score': 0.0,
                'log_amount': math.log(transaction.amount + 1),
                'rolling_mean_1h': 0.0,
                'rolling_std_1h': 1.0,
                'rolling_mean_24h': 0.0,
                'rolling_std_24h': 1.0
            }
        
        mean_amount = np.mean(amounts)
        std_amount = np.std(amounts) if len(amounts) > 1 else 1.0
        z_score = (transaction.amount - mean_amount) / std_amount if std_amount > 0 else 0.0
        
        one_hour_ago = transaction.ts - timedelta(hours=1)
        recent_amounts = [txn['amount'] for txn in customer_history 
                         if txn['ts'] >= one_hour_ago and txn['amount'] > 0]
        
        return {
            'z_score': z_score,
            'log_amount': math.log(transaction.amount + 1),
            'rolling_mean_1h': np.mean(recent_amounts) if recent_amounts else 0.0,
            'rolling_std_1h': np.std(recent_amounts) if len(recent_amounts) > 1 else 1.0,
            'rolling_mean_24h': mean_amount,
            'rolling_std_24h': std_amount
        }

    def _calculate_velocity_features(self, transaction: Transaction, customer_history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate velocity-based features"""
        five_min_ago = transaction.ts - timedelta(minutes=5)
        one_hour_ago = transaction.ts - timedelta(hours=1)
        one_day_ago = transaction.ts - timedelta(hours=24)
        
        recent_5m = [txn for txn in customer_history if txn['ts'] >= five_min_ago]
        recent_1h = [txn for txn in customer_history if txn['ts'] >= one_hour_ago]
        recent_24h = [txn for txn in customer_history if txn['ts'] >= one_day_ago]
        
        return {
            'txn_count_5m': len(recent_5m),
            'txn_count_1h': len(recent_1h),
            'txn_count_24h': len(recent_24h),
            'distinct_merchants_5m': len(set(txn['merchant_id'] for txn in recent_5m)),
            'distinct_merchants_1h': len(set(txn['merchant_id'] for txn in recent_1h)),
            'distinct_merchants_24h': len(set(txn['merchant_id'] for txn in recent_24h))
        }

    def _calculate_geo_features(self, transaction: Transaction, customer_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate geographic features"""
        distance_from_home = 0.0
        speed_from_last_txn = None
        country_change = False
        city_change = False
        
        if customer_history:
            last_txn = customer_history[0]
            country_change = last_txn.get('country') != transaction.country
            city_change = last_txn.get('city') != transaction.city
            
            if transaction.lat and transaction.lon and last_txn.get('lat') and last_txn.get('lon'):
                try:
                    distance = geodesic(
                        (last_txn['lat'], last_txn['lon']),
                        (transaction.lat, transaction.lon)
                    ).kilometers
                    time_diff = (transaction.ts - last_txn['ts']).total_seconds() / 3600
                    speed_from_last_txn = distance / time_diff if time_diff > 0 else 0.0
                except:
                    pass
        
        return {
            'distance_from_home': distance_from_home,
            'speed_from_last_txn': speed_from_last_txn,
            'country_change': country_change,
            'city_change': city_change
        }

    def _calculate_time_features(self, transaction: Transaction) -> Dict[str, Any]:
        """Calculate time-based features"""
        return {
            'hour_of_day': transaction.ts.hour,
            'day_of_week': transaction.ts.weekday(),
            'is_holiday': False,  # Simplified
            'is_weekend': transaction.ts.weekday() >= 5
        }

    def _calculate_merchant_features(self, transaction: Transaction, merchant_stats: Dict[str, Any]) -> Dict[str, float]:
        """Calculate merchant-based features"""
        return {
            'fraud_rate': merchant_stats.get('fraud_rate', 0.0),
            'mcc_fraud_rate': 0.01,  # Default
            'txn_count': merchant_stats.get('total_transactions', 0)
        }

    def _calculate_device_features(self, transaction: Transaction, customer_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate device and IP features"""
        device_change = False
        ip_change = False
        
        if customer_history:
            last_txn = customer_history[0]
            device_change = (last_txn.get('device_id') != transaction.device_id and 
                           transaction.device_id and last_txn.get('device_id'))
            ip_change = (last_txn.get('ip') != transaction.ip and 
                        transaction.ip and last_txn.get('ip'))
        
        return {
            'device_rarity': 1.0,  # Simplified
            'ip_rarity': 1.0,      # Simplified
            'device_change': device_change,
            'ip_change': ip_change
        }

    def _calculate_channel_features(self, transaction: Transaction) -> Dict[str, bool]:
        """Calculate channel-based features"""
        return {
            'card_present': transaction.channel == ChannelType.CARD_PRESENT,
            'web': transaction.channel == ChannelType.WEB,
            'app': transaction.channel == ChannelType.APP
        }

    async def _get_merchant_stats(self, merchant_id: str, db: DatabaseManager) -> Dict[str, Any]:
        """Get merchant statistics with caching"""
        if merchant_id in self.merchant_stats_cache:
            return self.merchant_stats_cache[merchant_id]
        
        stats = await db.get_merchant_stats(merchant_id)
        self.merchant_stats_cache[merchant_id] = stats
        return stats

    def _get_default_features(self, transaction: Transaction) -> FeatureVector:
        """Return default features when feature engineering fails"""
        return FeatureVector(
            amount=transaction.amount,
            amount_z_score=0.0,
            amount_log=math.log(transaction.amount + 1),
            amount_rolling_mean_1h=0.0,
            amount_rolling_std_1h=1.0,
            amount_rolling_mean_24h=0.0,
            amount_rolling_std_24h=1.0,
            txn_count_5m=0,
            txn_count_1h=0,
            txn_count_24h=0,
            distinct_merchants_5m=0,
            distinct_merchants_1h=0,
            distinct_merchants_24h=0,
            distance_from_home=0.0,
            speed_from_last_txn=None,
            country_change=False,
            city_change=False,
            hour_of_day=transaction.ts.hour,
            day_of_week=transaction.ts.weekday(),
            is_holiday=False,
            is_weekend=transaction.ts.weekday() >= 5,
            merchant_fraud_rate=0.0,
            mcc_fraud_rate=0.01,
            merchant_txn_count=0,
            device_rarity_score=1.0,
            ip_rarity_score=1.0,
            device_change=False,
            ip_change=False,
            channel_card_present=transaction.channel == ChannelType.CARD_PRESENT,
            channel_web=transaction.channel == ChannelType.WEB,
            channel_app=transaction.channel == ChannelType.APP,
            merchant_id_encoded=0.5,
            mcc_encoded=0.5,
            country_encoded=0.5
        )
