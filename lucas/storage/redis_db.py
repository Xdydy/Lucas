import redis
import pickle
from lucas.utils.logging import log as logging

class RedisDB:
    def __init__(self, host: str, port: int):
        self._redis_host = host
        self._redis_port = port
        self._pool = redis.ConnectionPool(host=self._redis_host, port=self._redis_port)
    def set(self, key: str, value):
        r = redis.Redis(connection_pool=self._pool)
        value = pickle.dumps(value)
        if r.set(key, value) is not True:
            logging.error(f"Failed to set key {key}")
            return False
        logging.info(f"Set key {key} succeed")
        return True
    def get(self, key: str):
        r = redis.Redis(connection_pool=self._pool)
        value = r.get(key)
        if value is None:
            logging.error(f"Failed to get key {key}")
            return None
        logging.info(f"Get key {key} succeed")
        return pickle.loads(value)
    def delete(self, key: str):
        r = redis.Redis(connection_pool=self._pool)
        if r.delete(key) == 0:
            logging.error(f"Failed to delete key {key}")
            return False
        logging.info(f"Delete key {key} succeed")
        return True