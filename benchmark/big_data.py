import matplotlib.pyplot as plt
import numpy as np
# 定义数据
categories = ['10MB','20MB','50MB','100MB']
values1 = [13.18,14.61,26.04,31.87] # data_size=100Mb
values2 = [6.65,9.87,18.61,25.04] # data_size=100Mb

bar_width = 0.35
x = np.arange(len(categories))
# 绘制柱状图
plt.bar(x - bar_width / 2, values1, width=bar_width, color='r', label='baseline')
plt.bar(x + bar_width / 2, values2, width=bar_width, color='b', label='lucas workflow')

# 添加标题和标签
plt.title('WordCount\'s Latecy of Different Workloads')
plt.xlabel('Data\'s size')
plt.ylabel('Latecy (s)')

plt.xticks(x, categories)
plt.legend()

# 显示图形
plt.savefig('big_data.png')