from lucas import Runtime, function,create_handler,workflow
from lucas import Workflow
from lucas.workflow import Lambda
import numpy as np
from lucas.workflow.executor import MulThreadExecutor



def split(matrix_size, split_num):
    block_size = matrix_size // split_num
    A = np.random.rand(matrix_size, matrix_size)
    A = np.dot(A, A.T)

    results = []
    for i in range(0, matrix_size, block_size):
        row = []
        for j in range(0, matrix_size, block_size):
            block = A[i:i + block_size, j:j + block_size]
            row.append(block)
        results.append(row)

    return results

def compute(block,i,j):
    if i == j:
        # 对角块的 Cholesky 分解
        L_block = np.linalg.cholesky(block)
        return L_block
    else:
        # 非对角块的计算
        L_top_left = L[j:j_end, j:j_end]
        L_top_left_inv = np.linalg.inv(L_top_left)
        L_block = np.dot(A_block, L_top_left_inv.T)
        return L_block

@workflow
def cholesky_workflow(wf:Workflow):
    matrix_size = 5000
    split_num = 2
    block_size = matrix_size // split_num
    blocks = split(matrix_size=matrix_size, split_num=split_num)
    L = []
    for i in range(matrix_size):
        L.append([Lambda()]*matrix_size)
    for i in range(0, matrix_size, block_size):
        for j in range(0, i+block_size, block_size):
            i_end = min(i + block_size, matrix_size)
            j_end = min(j + block_size, matrix_size)
            if i == j:
                L[i:i_end, j:j_end] = wf.func(compute, blocks[i][j], i,j)
            else:
                L_top_left = L[j:j_end, j:j_end]
                L_top_left_inv = wf.func(np.linalg.inv, L_top_left)
                L_block = wf.func(np.dot, blocks[i][j], L_top_left_inv.T)
                L[i:i_end, j:j_end] = L_block
    return L

import time
start_time = time.time()
cholesky_workflow.execute(MulThreadExecutor)
end_time = time.time()
print(f'time: {end_time - start_time}')
