class ActorConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        pass

class ActorClass:
    def __init__(self, cls, config: ActorConfig):
        self._cls = cls
        self._config = config
        self._instance = None

    def onClassInit(self):
        pass    
    
    def export(self, *args, **kwargs):
        """
        导出类实例
        """
        try:
            self._instance = self._cls(*args, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to create instance of class {self._cls.__name__}: {e}")
        from .. import routeBuilder
        routeBuilder.actor(self._config.name).set_actor(self._instance)
        self.onClassInit()
        return self._instance
    
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