def func(**kwargs):
    print(kwargs)

a = {
    'a': 'b',
    'c': 'd'
}

print(func(**a))