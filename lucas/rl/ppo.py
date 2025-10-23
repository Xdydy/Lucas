from lucas import actor
class PPOPipeline:
    def __init__(self, model):
        self._model = model
        self._wrapper = None
        self._dependency = None
        self._provider = None
        self._name = None
        self._venv = None

    def set_wrapper(self, wrapper):
        self._wrapper = wrapper
    def set_dependency(self, dependency):
        self._dependency = dependency
    def set_provider(self, provider):
        self._provider = provider
    def set_name(self, name):
        self._name = name
    def set_venv(self, venv):
        self._venv = venv
    def export(self):

        @actor(
            wrapper=self._wrapper,
            dependency=self._dependency,
            provider=self._provider,
            name=self._name,
            venv=self._venv
        )
        class PPOTrainer:
            def __init__(self2):
                self2._model = self._model
            def train(self2, total_timesteps):
                self2._model.learn(total_timesteps=total_timesteps)
            def get_model(self2):
                return self2._model
        return PPOTrainer