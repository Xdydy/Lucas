import os
os.environ['provider'] = 'cluster'
from lucas import function
from lucas.cluster.client import Context
from lucas.cluster.scheduler import Scheduler
context = Context.create_context()
scheduler = Scheduler()
context.set_scheduler(scheduler)

@function
def func(a,b,c):
    return a+b+c

func = func.export()
result = func({'a':1,'b':2,'c':3})
print(result)
