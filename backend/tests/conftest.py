"""
Pytest fixtures for testing.
"""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base
from app.models import (
    User, Author, Video, MetricSnapshot, Comment,
    CodingRecord, MediaFile, Transcript, Keyframe,
    AuditLog, SearchSession,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_user(db_session):
    """Create a test user."""
    user = User(
        username="test_coder",
        display_name="Test Coder",
        hashed_password="hashed_test_password",
        role="coder",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_author(db_session):
    """Create a test author."""
    author = Author(
        platform="douyin",
        author_id_hash="abc123hashed",
        author_name_public="测试作者",
        follower_count=1000,
        account_verified=True,
    )
    db_session.add(author)
    await db_session.commit()
    await db_session.refresh(author)
    return author


@pytest.fixture
async def test_video(db_session, test_author):
    """Create a test video."""
    video = Video(
        platform="douyin",
        platform_video_id="7123456789012345678",
        video_url="https://www.douyin.com/video/7123456789012345678",
        video_title="AI数字人带货测试视频",
        video_description="这是一个测试视频",
        hashtags=["AI数字人", "带货"],
        duration_seconds=60,
        collection_method="manual_import",
        data_source="manual_import",
        public_at_collection=True,
        author_id=test_author.id,
        collection_keyword="AI数字人",
        search_result_rank=1,
        search_sort_mode="comprehensive",
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video
