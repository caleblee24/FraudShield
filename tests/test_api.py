import pytest
import asyncio
from httpx import AsyncClient
from backend.app import app

@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data

@pytest.mark.asyncio
async def test_score_transaction():
    """Test transaction scoring endpoint"""
    transaction_data = {
        "amount": 100.0,
        "merchant_cat": "retail",
        "merchant_id": "TEST_MERCH",
        "mcc": "5411",
        "currency": "USD",
        "country": "US",
        "city": "New York",
        "lat": 40.7128,
        "lon": -74.0060,
        "channel": "card_present",
        "card_id": "TEST_CARD",
        "customer_id": "TEST_CUST",
        "device_id": "TEST_DEVICE",
        "ip": "192.168.1.1"
    }
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/score", json=transaction_data)
        assert response.status_code == 200
        data = response.json()
        assert "txn_id" in data
        assert "score" in data
        assert "is_alert" in data
        assert 0 <= data["score"] <= 1

@pytest.mark.asyncio
async def test_simulate_transaction():
    """Test transaction simulation endpoint"""
    simulation_data = {
        "scenario": "impossible_travel",
        "customer_id": "TEST_CUST",
        "amount": 500.0
    }
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/simulate", json=simulation_data)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "txn_id" in data
        assert "scenario" in data

@pytest.mark.asyncio
async def test_get_alerts():
    """Test alerts endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "total" in data
        assert isinstance(data["alerts"], list)

@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test Prometheus metrics endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # Check for Prometheus metrics format
        content = response.text
        assert "fraud_detector_requests_total" in content
