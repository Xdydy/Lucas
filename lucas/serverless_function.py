class Metadata:
    def __init__(self, id, params, namespace, router, request_type, redis_db, producer):
        self._id = id # id of request
        self._params = params # input value of funcion
        self._namespace = namespace # namespace of function
        self._router = router # router for all the funcs
        self._type = request_type # type of request
        self._redis_db = redis_db # redis db
        self._rocketmq_producer = producer
    def __str__(self):
        return f"Metadata(id={self._id}, params={self._params}, namespace={self._namespace}, router={self._router}, type={self._type})"