import redis

db = redis.Redis(connection_pool=redis.ConnectionPool(host='10.0.0.100', port=6379))

db.set('key', 'value')