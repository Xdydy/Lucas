from lucas.workflow.dag import DAG
from ..protos.controller import controller_pb2

def convert_dag_to_proto(dag: DAG):
    """Convert lucas DAG object to proto DAG message"""
    dag_metadata = dag.metadata()
    proto_nodes = []

    for node_data in dag_metadata:
        if node_data["type"] == "ControlNode":
            # Create ControlNode proto message
            control_node = controller_pb2.ControlNode()
            control_node.Id = node_data["id"]
            control_node.Done = node_data["done"]
            control_node.FunctionName = node_data["functionname"]
            # Handle params map
            for key, value in node_data["params"].items():
                control_node.Params[key] = str(value)
            control_node.Current = node_data["current"]
            control_node.DataNode = node_data["data_node"]
            control_node.PreDataNodes.extend(node_data["pre_data_nodes"])
            control_node.FunctionType = node_data["functiontype"]

            # Create DAGNode with ControlNode
            dag_node = controller_pb2.DAGNode()
            dag_node.Type = "ControlNode"
            dag_node.ControlNode.CopyFrom(control_node)
            proto_nodes.append(dag_node)

        elif node_data["type"] == "DataNode":
            # Create DataNode proto message
            data_node = controller_pb2.DataNode()
            data_node.Id = node_data["id"]
            data_node.Done = node_data["done"]
            data_node.Lambda = node_data["lambda"]
            data_node.Ready = node_data["ready"]
            data_node.SufControlNodes.extend(node_data["suf_control_nodes"])
            data_node.ChildNode.extend(node_data["child_node"])

            # Handle optional fields
            if node_data["pre_control_node"] is not None:
                data_node.PreControlNode = node_data["pre_control_node"]
            if node_data["parent_node"] is not None:
                data_node.ParentNode = node_data["parent_node"]

            # Create DAGNode with DataNode
            dag_node = controller_pb2.DAGNode()
            dag_node.Type = "DataNode"
            dag_node.DataNode.CopyFrom(data_node)
            proto_nodes.append(dag_node)

    # Create and return proto DAG
    proto_dag = controller_pb2.DAG()
    proto_dag.Nodes.extend(proto_nodes)
    return proto_dag
