from typing import Callable
from ..runtime.runtime import Runtime, FaasitResult
# from faasit_runtime.utils import config



class RouteFunc:
    def __init__(self, name: str, handler: Callable[[Runtime], FaasitResult] = None) -> None:
        self.name = name
        self.handler = handler

    def set_handler(self, 
                    handler: Callable[[Runtime], FaasitResult]):
        self.handler = handler

class Route:
    def __init__(self, functions: list[RouteFunc]) -> None:
        self.functions = functions

class RouteBuilder:
    def __init__(self) -> None:
        self.funcs: list[RouteFunc] = []
        pass

    # This method is used to add a function to the workflow
    def func(self, funcName:str) -> RouteFunc:
        # create a new function
        newFunc = RouteFunc(funcName)
        self.funcs.append(newFunc)
        return newFunc

    # get all the funcs in the workflow
    def get_funcs(self) -> list[RouteFunc]:
        return self.funcs()

    # build the workflow
    def build(self) -> Route:
        return Route(self.funcs)
    
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
        raise ValueError(f'Function {name} not found in workflow')