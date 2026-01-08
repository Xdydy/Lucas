import matplotlib.pyplot as plt 
import json

lucas = json.load(open("lucas.json"))
ray = json.load(open("result.json"))
letters = ["a", "b", "c"]

fig, axs = plt.subplots(1,2,figsize=(16, 6), sharey=True)

for i in range(2,4):
    x = []
    y_ray = []
    y_lucas = []
    key = f"matrix_num=20,cluster_num={i}"
    for item in ray[key]:
        x.append(item[0]/10000)
        y_ray.append(item[1])
    for item in lucas[key]:
        y_lucas.append(item[1])
    axs[i-2].plot(x, y_lucas, marker="x", color="red", label="Lucas")
    axs[i-2].plot(x, y_ray, marker="o", color="blue", label="Ray")
    axs[i-2].legend()
    axs[i-2].set_title(f"({letters[i-2]}) matrix_num=20,cluster_num={i}")
    axs[i-2].set_xlabel(f"matrix_size $(10^4)$")

axs[0].set_ylabel("Latency (s)")
plt.suptitle("Concat's Latency of Different Matrix Size and Cluster Number", fontsize=16)
fig.savefig("ray1.png")
plt.close()

fig, axs = plt.subplots(1,2,figsize=(16, 6), sharey=True)
for i in range(2,4):
    x = []
    y_ray = []
    y_lucas = []
    key = f"matrix_size=100000,cluster_num={i}"
    for item in ray[key]:
        x.append(item[0]/10000)
        y_ray.append(item[1])
    for item in lucas[key]:
        y_lucas.append(item[1])
    axs[i-2].plot(x, y_lucas, marker="x", color="red", label="Lucas")
    axs[i-2].plot(x, y_ray, marker="o", color="blue", label="Ray")
    axs[i-2].legend()
    axs[i-2].set_title(f"({letters[i-2]}) matrix_size=100000,cluster_num={i}")
    axs[i-2].set_xlabel(f"matrix_num")

axs[0].set_ylabel("Latency (s)")
plt.suptitle("Concat's Latency of Different Matrix Number and Cluster Number", fontsize=16)
fig.savefig("ray2.png")
plt.close()
