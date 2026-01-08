import psutil
import os


pid = os.getpid()
process = psutil.Process(pid)

memory_info = process.memory_info()
print(memory_info.rss)
print(memory_info.vms)
print(memory_info.shared)

a = []
for i in range(1000000):
    a.append(i)

memory_info = process.memory_info()
print(memory_info.rss)
print(memory_info.vms)
print(memory_info.shared)