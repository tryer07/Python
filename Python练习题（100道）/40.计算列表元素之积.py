# 定义一个函数，该函数接收一个整数列表作为参数，并返回列表中所有元素的积

#方法一

# 定义函数
def multiply_list(lst):
    """
    计算列表中所有元素的积
    :param lst: 整数列表
    :return: 所有元素相乘的结果
    """
    result = 1          # 关键：初始值为 1（乘法单位元），不能是 0
    for i in lst:
        result *= i     # 逐个累乘
    return result

# 给定列表
Li = [1, 2, 3, 4, 5]

# 调用函数
print(multiply_list(Li))

#方法二

import math

def multiply_list(lst):
    return math.prod(lst)

#方法三

# from functools import reduce
#
# def multiply_list(lst):
#     return reduce(lambda x, y: x * y, lst)