import json
import asyncio
from typing import Dict, Any, Optional, Callable
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import os
import logging

logger = logging.getLogger(__name__)

class KafkaProducer:
    def __init__(self, bootstrap_servers: Optional[str] = None):
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", 
            "localhost:9092"
        )
        self.producer = None

    async def connect(self):
        """Initialize Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3
            )
            logger.info(f"Connected to Kafka at {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    async def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")

    async def send_transaction(self, topic: str, data: Dict[str, Any], key: Optional[str] = None):
        """Send transaction data to Kafka topic"""
        if not self.producer:
            await self.connect()
        
        try:
            future = self.producer.send(topic, value=data, key=key)
            # Wait for the send to complete
            record_metadata = future.get(timeout=10)
            logger.info(f"Sent message to {topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            return record_metadata
        except KafkaError as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            raise

    async def health_check(self) -> bool:
        """Check Kafka connectivity"""
        try:
            if not self.producer:
                await self.connect()
            # Try to get metadata for a test topic
            self.producer.partitions_for('test-topic')
            return True
        except Exception as e:
            logger.error(f"Kafka health check failed: {e}")
            return False

class KafkaConsumer:
    def __init__(self, topic: str, group_id: str, bootstrap_servers: Optional[str] = None):
        self.topic = topic
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", 
            "localhost:9092"
        )
        self.consumer = None
        self.running = False

    async def connect(self):
        """Initialize Kafka consumer"""
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                key_deserializer=lambda x: x.decode('utf-8') if x else None
            )
            logger.info(f"Connected to Kafka topic {self.topic} with group {self.group_id}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    async def close(self):
        """Close Kafka consumer"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

    async def start_consuming(self, message_handler: Callable[[Dict[str, Any]], None]):
        """Start consuming messages from Kafka topic"""
        if not self.consumer:
            await self.connect()
        
        self.running = True
        logger.info(f"Starting to consume messages from {self.topic}")
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    await message_handler(message.value)
                    # Commit the offset
                    self.consumer.commit()
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Continue processing other messages
                    continue
        except Exception as e:
            logger.error(f"Error in Kafka consumer: {e}")
        finally:
            await self.close()

    async def stop_consuming(self):
        """Stop consuming messages"""
        self.running = False
        logger.info("Stopping Kafka consumer")

class TransactionStreamProcessor:
    """Process transaction stream from Kafka"""
    
    def __init__(self, db_manager, fraud_detector, feature_engineer):
        self.db_manager = db_manager
        self.fraud_detector = fraud_detector
        self.feature_engineer = feature_engineer
        self.consumer = None

    async def start_processing(self):
        """Start processing transaction stream"""
        self.consumer = KafkaConsumer(
            topic="transactions.raw",
            group_id="fraud-detector-processor"
        )
        
        await self.consumer.start_consuming(self._process_transaction)

    async def _process_transaction(self, transaction_data: Dict[str, Any]):
        """Process individual transaction from stream"""
        try:
            # Convert to Transaction object
            from ..schemas import Transaction
            transaction = Transaction(**transaction_data)
            
            # Engineer features
            features = await self.feature_engineer.engineer_features(transaction, self.db_manager)
            
            # Score transaction
            score_result = await self.fraud_detector.score(features)
            
            # Store in database
            await self.db_manager.store_transaction(transaction, features, score_result)
            
            # Generate alert if needed
            if score_result.is_alert:
                from ..schemas import Alert
                import uuid
                
                alert = Alert(
                    alert_id=str(uuid.uuid4()),
                    txn_id=transaction.txn_id,
                    score=score_result.score,
                    timestamp=transaction.ts,
                    status="new",
                    explanation=score_result.explanation
                )
                await self.db_manager.store_alert(alert)
                
                # Send to alerts topic
                producer = KafkaProducer()
                await producer.connect()
                await producer.send_transaction("alerts.suspicious", alert.dict())
                await producer.close()
            
            logger.info(f"Processed transaction {transaction.txn_id} with score {score_result.score}")
            
        except Exception as e:
            logger.error(f"Error processing transaction: {e}")

class AlertStreamProcessor:
    """Process alert stream from Kafka"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.consumer = None

    async def start_processing(self):
        """Start processing alert stream"""
        self.consumer = KafkaConsumer(
            topic="alerts.suspicious",
            group_id="alert-processor"
        )
        
        await self.consumer.start_consuming(self._process_alert)

    async def _process_alert(self, alert_data: Dict[str, Any]):
        """Process individual alert from stream"""
        try:
            # Convert to Alert object
            from ..schemas import Alert
            alert = Alert(**alert_data)
            
            # Update alert in database
            await self.db_manager.store_alert(alert)
            
            logger.info(f"Processed alert {alert.alert_id} for transaction {alert.txn_id}")
            
        except Exception as e:
            logger.error(f"Error processing alert: {e}")

# Background task processors
async def start_transaction_processor(db_manager, fraud_detector, feature_engineer):
    """Start transaction stream processor in background"""
    processor = TransactionStreamProcessor(db_manager, fraud_detector, feature_engineer)
    await processor.start_processing()

async def start_alert_processor(db_manager):
    """Start alert stream processor in background"""
    processor = AlertStreamProcessor(db_manager)
    await processor.start_processing()
