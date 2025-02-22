import numpy as np
import time
def cholesky_blocked(A, block_size):
    n = A.shape[0]
    L = np.zeros((n, n))

    # 遍历矩阵块
    for i in range(0, n, block_size):
        for j in range(0, i + block_size, block_size):
            # 确定子矩阵的索引范围
            i_end = min(i + block_size, n)
            j_end = min(j + block_size, n)

            # 提取子矩阵
            A_block = A[i:i_end, j:j_end]

            if i == j:
                # 对角块的 Cholesky 分解
                L_block = np.linalg.cholesky(A_block)
                L[i:i_end, j:j_end] = L_block
            else:
                # 非对角块的计算
                L_top_left = L[j:j_end, j:j_end]
                L_top_left_inv = np.linalg.inv(L_top_left)
                L_block = np.dot(A_block, L_top_left_inv.T)
                L[i:i_end, j:j_end] = L_block

    return L

start_time = time.time()
# 示例矩阵
n = 5000  # 矩阵的大小
block_size = 2  # 块大小
A = np.random.rand(n, n)
A = np.dot(A, A.T)  # 确保矩阵是正定对称的

# 进行分块 Cholesky 分解
L = cholesky_blocked(A, block_size)
end_time = time.time()
# 验证分解结果
print(f'time: {end_time - start_time}')