from typing import Callable
from ..runtime.runtime import Runtime, FaasitResult
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .workflow import Workflow
    from lucas._private import Function

class RouteFunc:
    def __init__(self, name: str, handler: Callable[[Runtime], FaasitResult] = None) -> None:
        self.name = name
        self.handler = handler

    def set_handler(self, 
                    handler: Callable[[Runtime], FaasitResult]) -> "RouteFunc":
        self.handler = handler
        return self
    def set_function(self, function: "Function") -> "RouteFunc":
        self.function = function
        return self

class RouteClass:
    def __init__(self, name: str, cls = None):
        self.name = name
        self._cls = cls
    def set_actor(self, cls):
        self._cls = cls

class RouteWorkflow:
    def __init__(self, name: str, generate_workflow = None):
        self.name = name
        self._generate_workflow = generate_workflow
    def set_workflow(self, generate_workflow):
        self._generate_workflow = generate_workflow

class Route:
    def __init__(self, functions: list[RouteFunc], workflows:list[RouteWorkflow], actors:list[RouteClass]) -> None:
        self.functions = functions
        self.workflows = workflows
        self.actors = actors


class RouteBuilder:
    def __init__(self) -> None:
        self.funcs: list[RouteFunc] = []
        self.works: list[RouteWorkflow] = []
        self.actors: list[RouteClass] = []
        pass

    # This method is used to add a function to the workflow
    def func(self, funcName:str) -> RouteFunc:
        # create a new function
        newFunc = RouteFunc(funcName)
        self.funcs.append(newFunc)
        return newFunc

    def actor(self, actorName:str) -> RouteClass:
        newClass = RouteClass(actorName)
        self.actors.append(newClass)
        return newClass
    
    def workflow(self, workflowName:str) -> RouteWorkflow:
        newWork = RouteWorkflow(workflowName)
        self.works.append(newWork)
        return newWork

    # get all the funcs in the workflow
    def get_funcs(self) -> list[RouteFunc]:
        return self.funcs
    
    def get_works(self) -> list[RouteWorkflow]:
        return self.works

    # build the workflow
    def build(self) -> Route:
        return Route(self.funcs,self.works,self.actors)
    
class RouteRunner:
    def __init__(self, route:Route) -> None:
        # self.conf = config.get_function_container_config()
        self._route = route
        pass

    # def get_funcName(self) -> str:
    #     return self.conf['funcName']

    # def run(self, frt: FaasitRuntime, *args) -> FaasitResult:
    #     funcName = self.get_funcName()
    #     fn = self.route(funcName)
    #     return fn(frt, *args)
    
    def route(self, name: str) -> Callable[[Runtime], FaasitResult]:
        for func in self._route.functions:
            if func.name == name:
                return func.handler
        for work in self._route.workflows:
            if work.name == name:
                def handler(event, workflow_runner:RouteRunner, metadata):
                    wf = work._generate_workflow(workflow_runner,metadata)
                    return wf.execute(event)
                return handler
        raise ValueError(f'Function {name} not found in workflow')