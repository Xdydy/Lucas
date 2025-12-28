#!/bin/bash

PROTOC="python -m grpc_tools.protoc"
export PATH="$PATH:$HOME/go/bin"

# ACTOR_SRC=$(go list -f {{.Dir}} github.com/asynkron/protoactor-go/actor)
# ACTOR_PROTO=$ACTOR_SRC/actor.proto

PROTOC="$PROTOC -I ."
PROTO_SRC="*.proto ./executor/*.proto ./controller/*.proto ./cluster/*.proto"

PY_OUTPUTS="../lucas/actorc/protos"


for PY_OUTPUT in $PY_OUTPUTS; do
  echo "Generating protobuf files for Python: $PY_OUTPUT"

  if [ ! -d $PY_OUTPUT ]; then
    mkdir -p $PY_OUTPUT
  else
    find $PY_OUTPUT -type f -name "*_pb2.py" -delete
    find $PY_OUTPUT -type f -name "*_pb2.pyi" -delete
    find $PY_OUTPUT -type f -name "*_pb2_grpc.py" -delete
  fi

  $PROTOC --python_out=$PY_OUTPUT --pyi_out=$PY_OUTPUT --grpc_python_out=$PY_OUTPUT $PROTO_SRC
done
