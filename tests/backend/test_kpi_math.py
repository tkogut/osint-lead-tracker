import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from main import app, get_db, get_current_user
from database import AsyncSessionLocal
from models import User, RunPerformanceSnapshot, Lead
from sqlalchemy import select, delete

# Mock User dependency
async def override_current_user():
    return User(id=1, username="testadmin", role="admin")

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def setup_mock_data():
    # Setup FastAPI dependency overrides
    app.dependency_overrides[get_current_user] = override_current_user
    
    async with AsyncSessionLocal() as session:
        # Clean up database tables
        await session.execute(delete(RunPerformanceSnapshot))
        await session.execute(delete(Lead))
        await session.commit()
        
    yield
    
    # Clean up overrides
    app.dependency_overrides.clear()

@pytest.mark.anyio
async def test_kpi_math_computations(setup_mock_data):
    # 1. Test empty database (prevents division by zero)
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert data["yield_total_7d"] == 0
        assert data["yield_per_chunk"] == 0.0
        assert data["cost_per_run_avg_tokens"] == 0
        assert data["runs_count_7d"] == 0

    # 2. Add specific performance snapshots to verify formulas
    async with AsyncSessionLocal() as session:
        # Yield total: 10 + 20 = 30
        # Total chunks: 2 + 3 = 5
        # Chunks division result: 30 / 5 = 6.0
        # Average tokens per run: (1000 + 500 + 2000 + 1000) / 2 = 2250
        run1 = RunPerformanceSnapshot(
            account_id=1,
            source="Google",
            run_date=datetime.utcnow().strftime("%Y-%m-%d"),
            leads_generated=10,
            grounding_chunks_count=2,
            grounding_queries_count=5,
            input_tokens=1000,
            output_tokens=500,
            api_errors=0,
            circuit_breaker_triggered=False
        )
        run2 = RunPerformanceSnapshot(
            account_id=1,
            source="Google",
            run_date=datetime.utcnow().strftime("%Y-%m-%d"),
            leads_generated=20,
            grounding_chunks_count=3,
            grounding_queries_count=10,
            input_tokens=2000,
            output_tokens=1000,
            api_errors=1,
            circuit_breaker_triggered=True
        )
        session.add_all([run1, run2])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert data["yield_total_7d"] == 30
        assert data["total_chunks_analyzed_7d"] == 5
        # yield_per_chunk: 30 / 5 = 6.0
        assert data["yield_per_chunk"] == 6.0
        # total queries: 5 + 10 = 15
        assert data["total_queries_fired_7d"] == 15
        # input tokens: 1000 + 2000 = 3000
        assert data["input_tokens_7d"] == 3000
        # output tokens: 500 + 1000 = 1500
        assert data["output_tokens_7d"] == 1500
        # cost_per_run_avg_tokens: (3000 + 1500) / 2 runs = 2250
        assert data["cost_per_run_avg_tokens"] == 2250
        assert data["api_errors_7d"] == 1
        assert data["circuit_breaker_events_7d"] == 1
        assert data["runs_count_7d"] == 2
