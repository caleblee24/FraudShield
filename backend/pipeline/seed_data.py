import asyncio
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from ..schemas import Transaction, ChannelType
from ..utils.db import DatabaseManager

logger = logging.getLogger(__name__)

class DataSeeder:
    def __init__(self):
        self.db = DatabaseManager()
        
        # Sample data for realistic transactions
        self.merchants = [
            {"id": "MERCH001", "name": "Walmart", "category": "retail", "mcc": "5411", "fraud_rate": 0.01},
            {"id": "MERCH002", "name": "Amazon", "category": "online_retail", "mcc": "5942", "fraud_rate": 0.02},
            {"id": "MERCH003", "name": "Shell Gas", "category": "gas_station", "mcc": "5541", "fraud_rate": 0.03},
            {"id": "MERCH004", "name": "Starbucks", "category": "food", "mcc": "5814", "fraud_rate": 0.01},
            {"id": "MERCH005", "name": "Best Buy", "category": "electronics", "mcc": "5732", "fraud_rate": 0.04},
            {"id": "MERCH006", "name": "Target", "category": "retail", "mcc": "5411", "fraud_rate": 0.01},
            {"id": "MERCH007", "name": "Home Depot", "category": "hardware", "mcc": "5200", "fraud_rate": 0.02},
            {"id": "MERCH008", "name": "McDonald's", "category": "food", "mcc": "5814", "fraud_rate": 0.01},
            {"id": "MERCH009", "name": "CVS", "category": "pharmacy", "mcc": "5912", "fraud_rate": 0.01},
            {"id": "MERCH010", "name": "Suspicious Shop", "category": "electronics", "mcc": "5732", "fraud_rate": 0.15}
        ]
        
        self.locations = [
            {"country": "US", "city": "New York", "lat": 40.7128, "lon": -74.0060},
            {"country": "US", "city": "Los Angeles", "lat": 34.0522, "lon": -118.2437},
            {"country": "US", "city": "Chicago", "lat": 41.8781, "lon": -87.6298},
            {"country": "US", "city": "Houston", "lat": 29.7604, "lon": -95.3698},
            {"country": "US", "city": "Phoenix", "lat": 33.4484, "lon": -112.0740},
            {"country": "UK", "city": "London", "lat": 51.5074, "lon": -0.1278},
            {"country": "CA", "city": "Toronto", "lat": 43.6532, "lon": -79.3832},
            {"country": "MX", "city": "Mexico City", "lat": 19.4326, "lon": -99.1332}
        ]
        
        self.customers = [
            {"id": "CUST001", "home_country": "US", "home_city": "New York"},
            {"id": "CUST002", "home_country": "US", "home_city": "Los Angeles"},
            {"id": "CUST003", "home_country": "US", "home_city": "Chicago"},
            {"id": "CUST004", "home_country": "UK", "home_city": "London"},
            {"id": "CUST005", "home_country": "CA", "home_city": "Toronto"}
        ]

    async def seed_data(self, num_transactions: int = 1000):
        """Seed the database with sample transaction data"""
        try:
            await self.db.connect()
            logger.info(f"Seeding {num_transactions} transactions...")
            
            # Generate transactions
            transactions = self._generate_transactions(num_transactions)
            
            # Insert transactions in batches
            batch_size = 100
            for i in range(0, len(transactions), batch_size):
                batch = transactions[i:i + batch_size]
                await self._insert_transaction_batch(batch)
                logger.info(f"Inserted batch {i//batch_size + 1}/{(len(transactions) + batch_size - 1)//batch_size}")
            
            logger.info("Data seeding completed successfully!")
            
        except Exception as e:
            logger.error(f"Error seeding data: {e}")
            raise
        finally:
            await self.db.close()

    def _generate_transactions(self, num_transactions: int) -> List[Dict[str, Any]]:
        """Generate realistic transaction data"""
        transactions = []
        
        # Generate transactions over the last 30 days
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)
        
        for i in range(num_transactions):
            # Random timestamp within the last 30 days
            timestamp = start_time + timedelta(
                seconds=random.randint(0, int((end_time - start_time).total_seconds()))
            )
            
            # Select random customer and merchant
            customer = random.choice(self.customers)
            merchant = random.choice(self.merchants)
            location = random.choice(self.locations)
            
            # Generate realistic amount based on merchant category
            amount = self._generate_realistic_amount(merchant["category"])
            
            # Determine if this should be a fraud transaction
            is_fraud = self._determine_fraud(merchant, customer, location, amount)
            
            # Generate transaction
            transaction = {
                "txn_id": str(uuid.uuid4()),
                "ts": timestamp,
                "amount": amount,
                "merchant_cat": merchant["category"],
                "merchant_id": merchant["id"],
                "mcc": merchant["mcc"],
                "currency": "USD",
                "country": location["country"],
                "city": location["city"],
                "lat": location["lat"] + random.uniform(-0.01, 0.01),  # Add some variation
                "lon": location["lon"] + random.uniform(-0.01, 0.01),
                "channel": self._select_channel(),
                "card_id": f"CARD_{customer['id']}_{random.randint(1, 3)}",
                "customer_id": customer["id"],
                "device_id": f"DEVICE_{customer['id']}_{random.randint(1, 2)}",
                "ip": self._generate_ip(),
                "is_fraud": is_fraud
            }
            
            transactions.append(transaction)
        
        # Sort by timestamp
        transactions.sort(key=lambda x: x["ts"])
        return transactions

    def _generate_realistic_amount(self, merchant_category: str) -> float:
        """Generate realistic transaction amounts based on merchant category"""
        if merchant_category == "gas_station":
            return round(random.uniform(20, 80), 2)
        elif merchant_category == "food":
            return round(random.uniform(5, 50), 2)
        elif merchant_category == "retail":
            return round(random.uniform(10, 200), 2)
        elif merchant_category == "electronics":
            return round(random.uniform(50, 1000), 2)
        elif merchant_category == "online_retail":
            return round(random.uniform(20, 500), 2)
        elif merchant_category == "hardware":
            return round(random.uniform(30, 300), 2)
        elif merchant_category == "pharmacy":
            return round(random.uniform(10, 100), 2)
        else:
            return round(random.uniform(10, 100), 2)

    def _determine_fraud(self, merchant: Dict, customer: Dict, location: Dict, amount: float) -> bool:
        """Determine if a transaction should be marked as fraud"""
        fraud_probability = 0.0
        
        # Base fraud rate from merchant
        fraud_probability += merchant["fraud_rate"]
        
        # Geographic anomaly (different country from customer's home)
        if location["country"] != customer["home_country"]:
            fraud_probability += 0.1
        
        # High amount anomaly
        if amount > 500:
            fraud_probability += 0.05
        
        # Suspicious merchant
        if merchant["fraud_rate"] > 0.1:
            fraud_probability += 0.2
        
        # Random fraud injection for demonstration
        if random.random() < 0.02:  # 2% random fraud
            fraud_probability += 0.5
        
        return random.random() < fraud_probability

    def _select_channel(self) -> str:
        """Select transaction channel"""
        channels = [ChannelType.CARD_PRESENT, ChannelType.WEB, ChannelType.APP]
        weights = [0.4, 0.4, 0.2]  # Card present and web are more common
        return random.choices(channels, weights=weights)[0]

    def _generate_ip(self) -> str:
        """Generate realistic IP address"""
        return f"{random.randint(192, 223)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

    async def _insert_transaction_batch(self, transactions: List[Dict[str, Any]]):
        """Insert a batch of transactions into the database"""
        async with self.db.pool.acquire() as conn:
            for transaction in transactions:
                await conn.execute("""
                    INSERT INTO transactions (
                        txn_id, ts, amount, merchant_cat, merchant_id, mcc, currency,
                        country, city, lat, lon, channel, card_id, customer_id, device_id, ip, is_fraud
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                    ON CONFLICT (txn_id) DO NOTHING
                """, 
                    transaction["txn_id"], transaction["ts"], transaction["amount"],
                    transaction["merchant_cat"], transaction["merchant_id"], transaction["mcc"],
                    transaction["currency"], transaction["country"], transaction["city"],
                    transaction["lat"], transaction["lon"], transaction["channel"],
                    transaction["card_id"], transaction["customer_id"], transaction["device_id"],
                    transaction["ip"], transaction["is_fraud"]
                )

    async def create_fraud_scenarios(self):
        """Create specific fraud scenarios for testing"""
        await self.db.connect()
        
        scenarios = [
            # Impossible travel scenario
            {
                "description": "Impossible travel - same card used in different countries within minutes",
                "transactions": [
                    {
                        "ts": datetime.utcnow() - timedelta(minutes=5),
                        "amount": 100.0,
                        "merchant_cat": "retail",
                        "merchant_id": "MERCH001",
                        "mcc": "5411",
                        "country": "US",
                        "city": "New York",
                        "lat": 40.7128,
                        "lon": -74.0060,
                        "channel": ChannelType.CARD_PRESENT,
                        "card_id": "CARD_FRAUD_001",
                        "customer_id": "CUST_FRAUD_001",
                        "device_id": "DEVICE_FRAUD_001",
                        "ip": "192.168.1.1",
                        "is_fraud": True
                    },
                    {
                        "ts": datetime.utcnow() - timedelta(minutes=2),
                        "amount": 500.0,
                        "merchant_cat": "electronics",
                        "merchant_id": "MERCH005",
                        "mcc": "5732",
                        "country": "UK",
                        "city": "London",
                        "lat": 51.5074,
                        "lon": -0.1278,
                        "channel": ChannelType.WEB,
                        "card_id": "CARD_FRAUD_001",  # Same card
                        "customer_id": "CUST_FRAUD_001",
                        "device_id": "DEVICE_FRAUD_002",
                        "ip": "10.0.0.1",
                        "is_fraud": True
                    }
                ]
            },
            # High velocity scenario
            {
                "description": "High velocity attack - rapid transactions",
                "transactions": [
                    {
                        "ts": datetime.utcnow() - timedelta(minutes=4),
                        "amount": 50.0,
                        "merchant_cat": "gas_station",
                        "merchant_id": "MERCH003",
                        "mcc": "5541",
                        "country": "US",
                        "city": "Chicago",
                        "lat": 41.8781,
                        "lon": -87.6298,
                        "channel": ChannelType.CARD_PRESENT,
                        "card_id": "CARD_FRAUD_002",
                        "customer_id": "CUST_FRAUD_002",
                        "device_id": "DEVICE_FRAUD_003",
                        "ip": "192.168.1.2",
                        "is_fraud": True
                    },
                    {
                        "ts": datetime.utcnow() - timedelta(minutes=3),
                        "amount": 75.0,
                        "merchant_cat": "food",
                        "merchant_id": "MERCH004",
                        "mcc": "5814",
                        "country": "US",
                        "city": "Chicago",
                        "lat": 41.8781,
                        "lon": -87.6298,
                        "channel": ChannelType.CARD_PRESENT,
                        "card_id": "CARD_FRAUD_002",
                        "customer_id": "CUST_FRAUD_002",
                        "device_id": "DEVICE_FRAUD_003",
                        "ip": "192.168.1.2",
                        "is_fraud": True
                    },
                    {
                        "ts": datetime.utcnow() - timedelta(minutes=2),
                        "amount": 200.0,
                        "merchant_cat": "retail",
                        "merchant_id": "MERCH001",
                        "mcc": "5411",
                        "country": "US",
                        "city": "Chicago",
                        "lat": 41.8781,
                        "lon": -87.6298,
                        "channel": ChannelType.CARD_PRESENT,
                        "card_id": "CARD_FRAUD_002",
                        "customer_id": "CUST_FRAUD_002",
                        "device_id": "DEVICE_FRAUD_003",
                        "ip": "192.168.1.2",
                        "is_fraud": True
                    }
                ]
            }
        ]
        
        for scenario in scenarios:
            logger.info(f"Creating scenario: {scenario['description']}")
            for transaction_data in scenario["transactions"]:
                transaction_data["txn_id"] = str(uuid.uuid4())
                await self._insert_transaction_batch([transaction_data])
        
        await self.db.close()
        logger.info("Fraud scenarios created successfully!")

async def main():
    """Main function to seed data"""
    seeder = DataSeeder()
    
    # Seed regular transaction data
    await seeder.seed_data(num_transactions=1000)
    
    # Create specific fraud scenarios
    await seeder.create_fraud_scenarios()

if __name__ == "__main__":
    asyncio.run(main())
