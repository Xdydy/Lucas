import os
import time
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from typing import Dict, Tuple
import json

context = Context.create_context()
matrix_size = 256
batch_size = 128
@function
def compute(matrixA: list[list], matrixB: list[list]) -> list:
    result = []
    for i in range(len(matrixA)):
        row = []
        for j in range(len(matrixB[0])):
            sum = 0
            for k in range(len(matrixB)):
                sum += matrixA[i][k] * matrixB[k][j]
            row.append(sum)
        result.append(row)
    return result

@function
def merge(a: list[list], b: list[list]) -> list:
    result = []
    for row_a, row_b in zip(a, b):
        merged_row = [x + y for x, y in zip(row_a, row_b)]
        result.append(merged_row)
    return result

@workflow(executor=ClusterExecutor)
def gemm(wf:Workflow):
    matrixA = [[1.0 for _ in range(matrix_size)] for _ in range(matrix_size)]
    matrixB = [[1.0 for _ in range(matrix_size)] for _ in range(matrix_size)]
    results = []
    for i in range(matrix_size // batch_size):
        for j in range(matrix_size // batch_size):
            # 分割矩阵: A矩阵的第i个batch，B矩阵的第j个batch
            sub_matrix_a = matrixA[j * (matrix_size // batch_size):(j + 1) * (matrix_size // batch_size)]
            sub_matrix_b = [row[i * (matrix_size // batch_size):(i + 1) * (matrix_size // batch_size)] for row in matrixB]
            c = wf.call("compute", {"matrixA": sub_matrix_a, "matrixB": sub_matrix_b})
            results.append(c)
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