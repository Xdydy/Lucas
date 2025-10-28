import uuid

class ActorConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        pass

class ActorInstance:
    def __init__(self, instance):
        self._id = str(uuid.uuid4())
        self._instance = instance

class ActorClass:
    def __init__(self, cls, config: ActorConfig):
        self._cls = cls
        self._config = config

    def onClassInit(self, instance) -> ActorInstance:
        pass    
    
    def export(self, *args, **kwargs) -> ActorInstance:
        """
        导出类实例
        """
        try:
            _instance = self._cls(*args, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to create instance of class {self._cls.__name__}: {e}")
        from .. import routeBuilder
        routeBuilder.actor(self._config.name).set_actor(_instance)
        actor_instance = self.onClassInit(_instance)
        return actor_instance
    
    # 调用方法转为类的方法
    def call(self, method_name: str, *args, **kwargs):
        if self._instance is None:
            raise RuntimeError("Instance not created. Call export() first.")
        method = getattr(self._instance, method_name, None)
        if not method:
            raise AttributeError(f"Method {method_name} not found in class {self._cls.__name__}")
        if not callable(method):
            raise TypeError(f"{method_name} is not callable")
        return method(*args, **kwargs)