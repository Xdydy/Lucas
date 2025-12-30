import os
import time
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from typing import Dict, Tuple
import json

context = Context.create_context()
matrix_size = 256
batch_size = 16
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

@workflow(executor=ClusterExecutor)
def gemm(wf:Workflow):
    results = []
    sub_matrix_as = []
    sub_matrix_bs = []
    for i in range(matrix_size // batch_size):
        sub_matrix_as.append(wf.call("splitA", {"i": i}))
        sub_matrix_bs.append(wf.call("splitB", {"j": i}))
    for i in range(matrix_size // batch_size):
        for j in range(matrix_size // batch_size):
            a = sub_matrix_as[i]
            b = sub_matrix_bs[j]
            result = wf.call("compute", {"matrixA": a, "matrixB": b})
            results.append(result)
    # while len(results) > 1:
    #     merged_results = []
    #     for i in range(0, len(results), 2):
    #         if i + 1 < len(results):
    #             merged = wf.call("merge", {"a": results[i], "b": results[i + 1]})
    #             merged_results.append(merged)
    #         else:
    #             merged_results.append(results[i])
    #     results = merged_results
    return results[0]

w_func = gemm.export()

start_t = time.time()
result = w_func()
end_t = time.time()


with open("result.json", "r") as f:
    data = json.load(f)
    if 'ad' in data:
        current_ad = data['ad']
    else:
        current_ad = {}
    current_ad.update({f"{matrix_size}x{batch_size}": end_t - start_t})
    data.update({"ad": current_ad})


with open("result.json", "w") as f:
    json.dump(data, f,indent=2)