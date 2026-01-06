import os
import time
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from typing import Dict, Tuple
import json

context = Context.create_context()
with open("input", "r") as f:
    line = f.readline()
    matrix_size, batch_size = map(int, line.split())

@function
def generate(matrix_size: int):
    matrixA = [[1.0 for _ in range(matrix_size)] for _ in range(matrix_size)]
    matrixB = [[1.0 for _ in range(matrix_size)] for _ in range(matrix_size)]
    return {"matrixA": matrixA, "matrixB": matrixB}

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
def splitA(matrix, i):
    matrixA = matrix['matrixA']
    return matrixA[i * batch_size:(i + 1) * batch_size]

@function
def splitB(matrix, j):
    matrixB = matrix['matrixB']
    return [row[j * batch_size:(j + 1) * batch_size] for row in matrixB]


splitA_fn = splitA.export()
splitB_fn = splitB.export()
compute_fn = compute.export()
generate_fn = generate.export()

start_t = time.time()
sub_matrix_as = []
sub_matrix_bs = []
matrix = generate_fn({"matrix_size": matrix_size})
for i in range(matrix_size // batch_size):
    sub_matrix_as.append(splitA_fn({"matrix": matrix,"i": i}))
    sub_matrix_bs.append(splitB_fn({"matrix": matrix,"j": i}))
for i in range(matrix_size // batch_size):
    for j in range(matrix_size // batch_size):
        a = sub_matrix_as[i]
        b = sub_matrix_bs[j]
        result = compute_fn({"matrixA": a, "matrixB": b})

end_t = time.time()

with open("result.json", "r") as f:
    data = json.load(f)
    if 'base' not in data:
        data['base'] = {}
    current_base = data['base']
    if f"matrix_size" not in current_base:
        current_base[f"matrix_size"] = {}
    
    data_matrix_size = current_base[f"matrix_size"]
    if f"{matrix_size}" not in data_matrix_size:
        data_matrix_size[f"{matrix_size}"] = []
    data_matrix_size[f"{matrix_size}"].append((batch_size, end_t - start_t))
    data_matrix_size[f"{matrix_size}"] = sorted(data_matrix_size[f"{matrix_size}"], key=lambda x: int(x[0]))

    data_matrix_size = dict(sorted(data_matrix_size.items(), key=lambda x: int(x[0])))

    current_base.update({f"matrix_size": data_matrix_size})
    current_base = dict(sorted(current_base.items()))
    data.update({"base": current_base})


with open("result.json", "w") as f:
    json.dump(data, f,indent=2)