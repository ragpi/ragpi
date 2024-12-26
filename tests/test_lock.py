import pytest
from unittest.mock import Mock, patch
from redis.lock import Lock
from redis.exceptions import LockError
from src.lock.service import LockService
from src.common.redis import RedisClient
from src.common.exceptions import ResourceLockedException

@pytest.fixture
def mock_redis_client() -> Mock:
    return Mock(RedisClient)

@pytest.fixture
def lock_service(mock_redis_client: Mock) -> LockService:
    return LockService(redis_client=mock_redis_client)

def test_lock_exists(lock_service: LockService, mock_redis_client: Mock) -> None:
    mock_redis_client.exists.return_value = 1
    assert lock_service.lock_exists("test_lock") is True
    mock_redis_client.exists.return_value = 0
    assert lock_service.lock_exists("test_lock") is False

def test_acquire_lock(lock_service: LockService, mock_redis_client: Mock) -> None:
    mock_lock = Mock(Lock)
    mock_lock.acquire.return_value = True
    mock_redis_client.lock.return_value = mock_lock
    lock = lock_service.acquire_lock("test_lock")
    assert lock is mock_lock

def test_acquire_lock_failure(lock_service: LockService, mock_redis_client: Mock) -> None:
    mock_lock = Mock(Lock)
    mock_lock.acquire.return_value = False
    mock_redis_client.lock.return_value = mock_lock
    with pytest.raises(ResourceLockedException):
        lock_service.acquire_lock("test_lock")

@pytest.mark.asyncio
async def test_renew_lock(lock_service: LockService) -> None:
    mock_lock = Mock(Lock)
    with patch("asyncio.sleep", return_value=None):
        await lock_service.renew_lock(mock_lock, extend_time=60, renewal_interval=30)
        mock_lock.extend.assert_called()

def test_release_lock(lock_service: LockService) -> None:
    mock_lock = Mock(Lock)
    lock_service.release_lock(mock_lock)
    mock_lock.release.assert_called()

def test_release_lock_failure(lock_service: LockService) -> None:
    mock_lock = Mock(Lock)
    mock_lock.release.side_effect = LockError
    with patch("logging.Logger.exception") as mock_logger_exception:
        lock_service.release_lock(mock_lock)
        mock_logger_exception.assert_called()
