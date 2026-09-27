#定义一个函数，该函数用于对列表进行去重处理，并返回一个新的列表，其中不包含任何重复元素

#定义函数

def remove_duplicates(list1):
    """
    对列表进行去重处理，并返回一个新的列表，其中不包含任何重复元素

    :param list1: 原始列表

    :return: 去重后的列表
    """

    #定义列表result保存去重后的元素

    result = []

    #遍历列表

    for i in list1:

        if i not in result:
            result.append(i)

    return result

#给定列表

list1 = [10,20,30,10,40,20]

#调用函数

print(remove_duplicates(list1))
