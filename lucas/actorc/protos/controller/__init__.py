# Controller protobuf types for Lucas
import sys
import os

# Add current directory to sys.path so that controller_pb2_grpc.py can import controller_pb2
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)