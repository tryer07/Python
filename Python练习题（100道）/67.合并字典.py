#定义一个函数，用于将两个字典合并

#导入copy模块，用于对象的拷贝操作

import copy

#定义函数

def merge_dicts(dict1,dict2):
    """
    合并两个字典
    :param dict1:
    :param dict2:
    :return: 合并后的字典
    """

    #拷贝dict1，避免修改原始字典

    merged_dict = copy.deepcopy(dict1)

    #使用update方法将dict2的键值对添加到merged_dict中

    merged_dict.update(dict2)

    return merged_dict

#给定两个字典

a = {'a':1,'b':2}

b = {'c':3,'d':4}

#调用函数并接收返回值

merged_dict = merge_dicts(a,b)

print(merged_dict)