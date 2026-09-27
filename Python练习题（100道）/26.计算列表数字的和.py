#定义一个函数，该函数用于计算并返回给定数字列表中所有数字的总和

#定义函数

def sum_of_list(number_list):
    """
    计算并返回给定数字列表中所有数字的总和

    :param number_list:数字列表

    :return:数字列表总和
    """
    #遍历数字列表

    total = 0

    for i in number_list:
        total += i

    return total

#给定数字列表

list1 = [1,2,3,4]

list2 = [20,4,8,21,15,25]

#调用函数并打印结果

print(sum_of_list(list1))

print(sum_of_list(list2))

