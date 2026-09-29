#定义一个函数，该函数接受一个列表newList作为参数。函数的功能是交换列表的第一个元素和最后一个元素，并返回交换后的列表。

#定义函数

def swap_first_last(newList):
    """
    交换列表的第一个元素和最后一个元素
    :param newList: 列表
    :return: 交换后的列表
    """

    newList[0], newList[-1] = newList[-1], newList[0]
    return newList

#交换列表元素

Li1 = [1,2,3]

Li2 = ['a','b','c','d','e']

#调用函数

print(swap_first_last(Li1))

print(swap_first_last(Li2))

