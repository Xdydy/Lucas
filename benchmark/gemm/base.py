import os
import time
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from typing import Dict, Tuple
import json

context = Context.create_context()
matrix_size = 512
batch_size = 32
matrixA = [[1.0 for _ in range(matrix_size)] for _ in range(matrix_size)]
matrixB = [[1.0 for _ in range(matrix_size)] for _ in range(matrix_size)]
@function
def compute(matrixA: list[list], matrixB: list[list]) -> list:
    result = []
    for i in range(len(matrixA)):
        row = []
        time.sleep(0.00001)
        for j in range(len(matrixB[0])):
            time.sleep(0.00001)
            sum = 0
            for k in range(len(matrixB)):
                sum += matrixA[i][k] * matrixB[k][j]
            row.append(sum)
        result.append(row)
    # time.sleep(1)
    return result

@function
def splitA(i):
    return matrixA[i * batch_size:(i + 1) * batch_size]

@function
def splitB(j):
    return [row[j * batch_size:(j + 1) * batch_size] for row in matrixB]


splitA_fn = splitA.export()
splitB_fn = splitB.export()
compute_fn = compute.export()

start_time = time.time()
sub_matrix_as = []
sub_matrix_bs = []
for i in range(matrix_size // batch_size):
    sub_matrix_as.append(splitA_fn({"i": i}))
    sub_matrix_bs.append(splitB_fn({"j": i}))
for i in range(matrix_size // batch_size):
    for j in range(matrix_size // batch_size):
        a = sub_matrix_as[i]
        b = sub_matrix_bs[j]
        result = compute_fn({"matrixA": a, "matrixB": b})

end_time = time.time()

with open("result.json", "r") as f:
    data = json.load(f)
    if 'base' in data:
        current_base = data['base']
    else:
        current_base = {}
    current_base.update({f"{matrix_size}x{batch_size}": end_time - start_time})
    data.update({"base": current_base})

with open("result.json", "w") as f:
    json.dump(data, f,indent=2)