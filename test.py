# import redis

# db = redis.Redis(connection_pool=redis.ConnectionPool(host='10.0.0.100', port=6379))

# db.set('key', 'value')
# db.set('key', 'value2')
# print(db.get('key'))

def f(a,b,c):
    return a+b+c 

def g(lists):
    s = 0
    for l in lists:
        s += l
    return s

def h(*args):
    s = 0
    for a in args:
        s += a
    return s

v = [1,2,3]
print(f(*v))
print(g([*v]))
print(h(*v))