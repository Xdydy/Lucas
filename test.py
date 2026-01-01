def funca(num):
    for i in range(num):
        yield i

def funcb():
    yield from funca(10)

g = funcb()
for i in g:
    print(i)