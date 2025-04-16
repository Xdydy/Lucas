import sys
sys.path.append("./protos")
from lucas import workflow, function, Runtime, Workflow, Function
from lucas.serverless_function import Metadata
from lucas.workflow.executor import Executor
from lucas.workflow.dag import DAGNode, DataNode, ControlNode
from lucas.utils.logging import log
from protos.controller import controller_pb2 as pb
import pickle
import uuid

class ActorRuntime(Runtime):
    def __init__(self, metadata: Metadata):
        super().__init__()
        self._input = metadata._params
        self._namespace = metadata._namespace
        self._router = metadata._router

    def input(self):
        return self._input

    def output(self, _out):
        return _out
    
    def get_result(self):
        return pb.ReturnResult(
        )
    
    def call(self, fnName:str, fnParams: dict):
        print(f"call {fnName}")
        fn = self._router.get(fnName)
        if fn is None:
            raise ValueError(f"Function {fnName} not found in router")

        return {
            'function': fnName,
            'params': fnParams,
            'data': fn(fnParams)
        }
    def tell(self, fnName:str, fnParams: dict):
        print("tell function here")
        fn = self._router.get(fnName)
        if fn is None:
            raise ValueError(f"Function {fnName} not found in router")
        
        return {
            'function': fnName,
            'params': fnParams,
            'data': fn(fnParams)
        }

class ActorFunction(Function):
    def onFunctionInit(self, fn):
        dependcy = self._config.dependency
        fn_name = self._config.name
        params = self._config.params
        venv = self._config.venv
        print("pickle function here")
        pb.AppendPyFunc(
            Name=fn_name,
            Params=params,
            Venv=venv,
            Requirements=dependcy,
            PickledObject=pickle.dumps('aaa')
        )
    def _transformfunction(self, fn):
        def actor_function(data: dict):
            # just use for local invoke
            from lucas import routeBuilder
            route = routeBuilder.build()
            route_dict = {}
            for function in route.functions:
                route_dict[function.name] = function.handler
            for workflow in route.workflows:
                route_dict[workflow.name] = function.handler
            metadata = Metadata(
                id=str(uuid.uuid4()),
                params=data,
                namespace=None,
                router=route_dict,
                request_type="invoke",
                redis_db=None,
                producer=None
            )
            rt = ActorRuntime(metadata)
            result = fn(rt)
            return result
        return actor_function

end = True
@function(wrapper=ActorFunction, dependency=['torch', 'numpy'], provider='actor', name='funca',params=['a'],venv='conda')
def funca(rt: Runtime):
    global end
    result = {**rt.input(), 'end':end}
    end = False
    return rt.output(result)

@function(wrapper=ActorFunction, dependency=['torch', 'numpy'],provider='actor', name='funcb',params=['a'],venv='conda')
def funcb(rt: Runtime):
    return rt.output(rt.input())


class ActorExecutor(Executor):
    def __init__(self, dag):
        super().__init__(dag)
        self._sesstionID = str(uuid.uuid4())
    def execute(self):
        while not self.dag.hasDone():
            task:list[DAGNode] = []
            for node in self.dag.get_nodes():
                if node._done:
                    continue
                if isinstance(node, DataNode):
                    if node.is_ready():
                        task.append(node)
                if isinstance(node, ControlNode):
                    if node.get_pre_data_nodes() == []:
                        task.append(node)

            _end = False
            while len(task) != 0:
                node = task.pop(0)
                node._done = True
                if isinstance(node, DataNode):
                    for control_node in node.get_succ_control_nodes():
                        control_node: ControlNode
                        control_node_metadata = control_node.metadata()
                        params = control_node_metadata['params']
                        fn_type = control_node_metadata['functiontype']
                        if fn_type == "remote": # 要调用的函数是远程函数时才需要
                            data_type = pb.Data.OBJ_ENCODED
                            data = node._ld.value
                            if isinstance(node._ld.value, pb.Data) and node._ld.value.Type == pb.Data.OBJ_REF: # 判断一下是什么类型的值
                                data_type = pb.Data.OBJ_REF

                            if data_type == pb.Data.OBJ_ENCODED: # 如果是实际值，就要序列化
                                data = pickle.dumps(data)
                            
                            rpc_data = pb.Data(
                                Type=data_type,
                                Data=data
                            )
                            
                            pb.AppendArg(
                                SessionID=self._sesstionID,
                                InstanceID=control_node_metadata['id'],
                                Name=control_node_metadata['functionname'],
                                Param=params[node._ld.getid()],
                                Value=rpc_data
                            )
                        # pb.AppendArg(
                        #     SessionID=self._sesstionID,
                        #     InstanceID=control_node_metadata['id'],
                        #     Name=control_node_metadata['functionname'],
                        #     Param=params[node._ld.getid()],
                        #     Value='aaa'
                        # )
                        log.info(f"{control_node.describe()} appargs {node._ld.value}")
                        if control_node.appargs(node._ld):
                            task.append(control_node)
                elif isinstance(node, ControlNode):
                    fn = node._fnfuncb
                    params = node._datas
                    result = fn(params)
                    log.info(f"{node.describe()} result {result}")
                    r_node: DataNode = node.get_data_node()
                    if node._fn_type == "local":
                        r_node.set_value(result)
                    elif node._fn_type == "remote":
                        data = result['data']
                        if 'end' in data and data['end'] == True:
                            _end = True
                            break
                        r_node.set_value(result['data'])
                    r_node.set_ready()
                    log.info(f"{node.describe()} calculate {r_node.describe()}")
                    if r_node.is_ready():
                        task.append(r_node)
            if _end:
                break
        result = None
        for node in self.dag.get_nodes():
            if isinstance(node, DataNode) and node._is_end_node:
                result = node._ld.value
                break
        self.dag.reset()
        return result


@workflow(executor=ActorExecutor)
def workflowfunc(wf: Workflow):
    _in = wf.input()
    
    a = wf.call('funca', {'a': _in['a']})
    b = wf.call('funcb', {'a': a['a']})
    return b



workflow_i = workflowfunc.generate()
dag = workflow_i.valicate()
import json
print(json.dumps(dag.metadata(fn_export=True),indent=2))


def actorWorkflowExportFunc(dict: dict):

    # just use for local invoke
    from lucas import routeBuilder
    route = routeBuilder.build()
    route_dict = {}
    for function in route.functions:
        route_dict[function.name] = function.handler
    for workflow in route.workflows:
        route_dict[workflow.name] = function.handler
    metadata = Metadata(
        id=str(uuid.uuid4()),
        params=dict,
        namespace=None,
        router=route_dict,
        request_type="invoke",
        redis_db=None,
        producer=None
    )
    rt = ActorRuntime(metadata)
    workflowfunc.set_runtime(rt)
    workflow = workflowfunc.generate()
    return workflow.execute()


workflow_func = workflowfunc.export(actorWorkflowExportFunc)
print("----first execute----")
workflow_func({'a': 1})
print("----second execute----")
workflow_func({'a': 2})