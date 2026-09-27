#定义一个函数，该函数用于实现两个变量值的互换

#用户输入两个变量的值

a = int(input('请输入第一个变量的值：'))
b = int(input('请输入第二个变量的值：'))

#定义函数

def swap_values(a, b):
    """
    交换两个变量的值
    :param a: 第一个变量
    :param b: 第二个变量
    :return: 交换后的两个变量
    """

    a, b = b, a

    return a, b

#调用函数并打印结果

print(swap_values(a, b))


