from lucas.workflow import WorkflowContext
from typing import Callable, Any
from flask import Flask, request, jsonify
class Serve:
    def __init__(self):
        self._route: dict[str, Callable[..., Any]] = {}
        self._app = Flask(__name__)
        self._workflow_func = None
    
    def set_workflow_func(self, fn):
        self._workflow_func = fn

    def add_route(self, path: str, workflow_context: WorkflowContext):
        fn = workflow_context.export(self._workflow_func)
        def handler():
            input_data = request.get_json()
            result = fn(input_data)
            return jsonify({'status': 1, 'result': result}), 200
        handler.__name__ = f"handler_{path.replace('/', '_')}"
        self._route[path] = handler

    def serve(self, **kwargs):
        for path, handler in self._route.items():
            self._app.post(path)(handler)
        self._app.run(**kwargs)
    