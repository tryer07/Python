#定义一个函数，该函数接收一个字典作为参数，并返回该字典中所有值的总和

#定义函数

def sum_of_dict_values(dictionary):
    """
    计算并返回字典中所有值的总和
    :param dictionary:字典
    :return: 字典中所有值的总和
    """
    #定义变量保存总和

    result = 0

    #获取字典中所有值

    for values in dictionary.values():

        result += values

    return result

#给定字典

example_dict = {'a':100,'b':200,'c':300}

#调用函数

total = sum_of_dict_values(example_dict)

print(total)
