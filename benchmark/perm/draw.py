import matplotlib.pyplot as plt
import numpy as np
# 定义数据
with open("base.txt", "r") as f:
    lines = f.readlines()
values_base = [float(line.strip().split()[-1]) for line in lines]
with open("ad.txt", "r") as f:
    lines = f.readlines()
values_ad = [float(line.strip().split()[-1]) for line in lines]
categories = ['1000','2000','3000','4000']
bar_width = 0.25
x = np.arange(len(categories))
# 绘制柱状图
plt.bar(x - bar_width / 2 , values_base, width=bar_width, color='r', label='baseline')
plt.bar(x + bar_width / 2, values_ad, width=bar_width, color='b', label='DAG Execution')

# plt.plot(x, values_base, marker='o', color='r', label='Robin')
# plt.plot(x, values_path, marker='s', color='g', label='Key Path')

# 添加标题和标签
plt.title('DAG\'s Execution Latency of Different Workloads')
plt.xlabel('Data\'s size')
plt.ylabel('Latency (s)')

plt.xticks(x, categories)
plt.legend()

# 显示图形
plt.savefig('result.png')