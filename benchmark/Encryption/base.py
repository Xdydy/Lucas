import os
import time
os.environ['provider'] = 'cluster'
from lucas import function, workflow, Workflow
from lucas.cluster.client import Context, ClusterExecutor
from lucas.cluster.scheduler import RobinScheduler
from typing import Dict, Tuple
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

context = Context.create_context()
scheduler = RobinScheduler()
context.set_scheduler(scheduler)

@function
def generate_symmetric_key(key_size: int = 32) -> bytes:
    """
    生成对称加密密钥
    参数:
        key_size: 密钥长度（字节），16=AES-128, 24=AES-192, 32=AES-256
    返回:
        随机生成的对称密钥
    """
    start_time = time.time()
    
    if key_size not in [16, 24, 32]:
        raise ValueError("密钥长度必须是16、24或32字节")
    
    # 生成随机密钥
    key = get_random_bytes(key_size)
    
    print(f"已生成 {key_size*8}位对称密钥 (耗时: {time.time()-start_time:.3f}s)")
    return key

@function
def generate_plaintext(size_kb: int = 1) -> bytes:
    """
    生成指定大小的明文文本
    参数:
        size_kb: 明文大小（KB）
    返回:
        随机生成的明文字节串
    """
    start_time = time.time()
    
    # 生成随机明文
    plaintext = get_random_bytes(size_kb * 1024)
    
    print(f"已生成 {size_kb}KB 明文 (耗时: {time.time()-start_time:.3f}s)")
    return plaintext

@function
def encrypt_with_aes(plaintext: bytes, key: bytes) -> bytes:
    """
    使用AES-CBC加密明文
    返回值: 密文字节串（包含IV + 密文）
    """
    start_time = time.time()
    
    # 验证密钥长度
    if len(key) not in [16, 24, 32]:
        raise ValueError("密钥长度必须是16、24或32字节")
    
    # 生成IV
    iv = get_random_bytes(16)
    
    # AES-CBC加密
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(plaintext, AES.block_size)
    ciphertext = cipher.encrypt(padded_data)
    
    # 返回IV + 密文
    result = iv + ciphertext
    
    return result



@workflow(executor=ClusterExecutor)
def symmetric_encryption_workflow(wf:Workflow) -> dict:
    """
    完整的对称加密工作流
    返回值: 包含执行结果的字典
    """
    _in = wf.input()
    data_size_kb = _in['data_size_kb']
    key_size = _in['key_size']
    
    
    # 阶段2: 生成密钥
    key = wf.call("generate_symmetric_key", {
        "key_size": key_size  # AES-256
    })
    # 阶段1: 生成明文
    plaintext = wf.call("generate_plaintext", {
        "size_kb": data_size_kb
    })
    
    # 阶段3: 加密
    encrypted_data = wf.call("encrypt_with_aes", {
        "plaintext": plaintext,
        "key": key
    })
    
    
    
    return encrypted_data

dag = symmetric_encryption_workflow.generate().valicate()
scheduler.analyze(dag)
w_func = symmetric_encryption_workflow.export()

payloads = [
    {"data_size_kb": 1000, "key_size": 16},
    {"data_size_kb": 2000, "key_size": 16},
    {"data_size_kb": 3000, "key_size": 16},
    {"data_size_kb": 4000, "key_size": 16},
]
out = []
for payload in payloads:
    start_t = time.time()
    result = w_func(payload)
    end_t = time.time()
    print(f"Payload: {payload}, Execution time: {end_t - start_t} seconds") 
    out.append((payload, end_t - start_t))

with open("base.txt", "w") as f:
    for record in out:
        f.write(f"{record[0]} {record[1]}\n")