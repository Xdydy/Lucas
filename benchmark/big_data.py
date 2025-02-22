import matplotlib.pyplot as plt
import numpy as np
# 定义数据
categories = ['100x100', '500x500', '1000x1000', '5000x5000']
values1 = [0.93, 1.23, 1.78, 6.61] # data_size=10Mb
values2 = [1.43, 2.03, 4.36, 11.42] # data_size=100Mb

bar_width = 0.35
x = np.arange(len(categories))
# 绘制柱状图
plt.bar(x - bar_width / 2, values1, width=bar_width, color='r', label='data_size=10Mb')
plt.bar(x + bar_width / 2, values2, width=bar_width, color='b', label='data_size=100Mb')

# 添加标题和标签
plt.title('cholesky\'s Latecy of Different Workloads')
plt.xlabel('matrix\'s size')
plt.ylabel('Latecy')

plt.xticks(x, categories)
plt.legend()

# 显示图形
plt.savefig('bar.png')