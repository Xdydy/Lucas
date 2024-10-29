def Y(f):
    return (lambda x: f(lambda v: x(x)(v)))(lambda x: f(lambda v: x(x)(v)))

# 斐波那契函数的定义
def fib(f):
    def inner(n):
        if n <= 1:
            return n
        else:
            a = f(n-1)
            b = f(n-2)
            return a + b
    return inner

# 得到斐波那契函数
fibonacci = Y(fib)

# 测试斐波那契函数
print(fibonacci(10))  # 输出 55
