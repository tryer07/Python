#定义一个函数，该函数用于移除第一个列表中所有第二个列表中含有的元素

#定义函数

def remove_elements(list1, list2):
    """
    移除第一个列表中所有第二个列表中含有的元素
    :param list1: 第一个列表
    :param list2: 第二个列表
    :return: 移除元素后的列表
    """
    #遍历list2

    for i in list2:

        #如果i在list1中，则移除

        if i in list1:
            list1.remove(i)

    return list1

#给定列表

list1 = [3,5,7,9,11,13]

list2 = [7,11]

#调用函数并打印结果

print(remove_elements(list1, list2))

