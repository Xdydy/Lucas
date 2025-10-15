def sum(*args):
    res = 0
    for arg in args:
        res += arg
    return res

a = [1,2,3,4]
print(sum(*a))   