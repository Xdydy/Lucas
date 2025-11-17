from lucas.workflow.dag import DAG
from protos.controller import controller_pb2

def to_proto_append_dag_node_list(dag: DAG, session_id: str = "") -> list[controller_pb2.AppendDAGNode]:
    """Convert lucas DAG object to list of AppendDAGNode messages
    
    According to the latest DAG node definition:
    - ControlNode: Id, FunctionName, Params, Current, DataNode, PreDataNodes, FunctionType
    - DataNode: Id, Lambda, SufControlNodes, PreControlNode (optional), ParentNode (optional), ChildNode
    - DAGNodeType: DAG_NODE_TYPE_CONTROL (1) or DAG_NODE_TYPE_DATA (2)
    
    Args:
        dag: DAG object from lucas workflow
        session_id: Session ID for the DAG execution (optional)
    
    Returns:
        List of AppendDAGNode messages ready to be sent to controller
    """
    dag_metadata = dag.metadata()
    proto_nodes = []

    for node_data in dag_metadata:
        if node_data["type"] == "ControlNode":
            # Create ControlNode proto message
            control_node = controller_pb2.ControlNode()
            control_node.Id = node_data["id"]
            control_node.FunctionName = node_data["functionname"]
            
            # Handle params map (lambda_id -> parameter_name)
            for lambda_id, param_name in node_data["params"].items():
                control_node.Params[lambda_id] = str(param_name)
            
            control_node.Current = node_data["current"]
            # data_node is already an ID string from metadata()
            control_node.DataNode = node_data.get("data_node", "")
            # pre_data_nodes is already a list of ID strings from metadata()
            control_node.PreDataNodes.extend(node_data.get("pre_data_nodes", []))
            control_node.FunctionType = node_data["functiontype"]

            # Create AppendDAGNode with ControlNode
            dag_node = controller_pb2.AppendDAGNode()
            dag_node.SessionID = session_id
            dag_node.Type = controller_pb2.DAGNodeType.DAG_NODE_TYPE_CONTROL
            dag_node.ControlNode.CopyFrom(control_node)
            proto_nodes.append(dag_node)

        elif node_data["type"] == "DataNode":
            # Create DataNode proto message
            data_node = controller_pb2.DataNode()
            data_node.Id = node_data["id"]
            data_node.Lambda = node_data["lambda"]
            # suf_control_nodes is already a list of ID strings from metadata()
            data_node.SufControlNodes.extend(node_data.get("suf_control_nodes", []))
            # child_node is already a list of ID strings from metadata()
            data_node.ChildNode.extend(node_data.get("child_node", []))

            # Handle optional fields (PreControlNode and ParentNode)
            # These are already ID strings or None from metadata()
            if node_data.get("pre_control_node") is not None:
                data_node.PreControlNode = node_data["pre_control_node"]
            if node_data.get("parent_node") is not None:
                data_node.ParentNode = node_data["parent_node"]

            # Create AppendDAGNode with DataNode
            dag_node = controller_pb2.AppendDAGNode()
            dag_node.SessionID = session_id
            dag_node.Type = controller_pb2.DAGNodeType.DAG_NODE_TYPE_DATA
            dag_node.DataNode.CopyFrom(data_node)
            proto_nodes.append(dag_node)

    return proto_nodes
