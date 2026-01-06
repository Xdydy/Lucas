import matplotlib.pyplot as plt
import numpy as np

# 创建示例数据
np.random.seed(42)
datas = []
data1 = np.random.uniform(10, 10.5, 100)
datas.append(data1)
data2 = np.random.uniform(13.0, 13.5, 100)
datas.append(data2)
data3 = np.random.uniform(10.3, 10.8, 100)
datas.append(data3)

print(data1)
print(data2)
print(data3)

# 创建图形
plt.figure(figsize=(6, 5))

# 绘制箱型图
plt.boxplot(datas, 
            tick_labels=['Normal', 'Execute Without Replay', 'Execute With Replay'],
            widths=0.6,
            patch_artist=True,  # 填充颜色
            showmeans=True,     # 显示均值
            meanline=True,      # 均值用线表示
            showfliers=True)    # 显示离群值

# 添加标题和标签
plt.title('Execution Time of Different Execution Types', fontsize=14, fontweight='bold')
plt.xlabel('Execution Type', fontsize=12)
plt.ylabel('Execution Time(s)', fontsize=12)
plt.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig('boxplot.png')