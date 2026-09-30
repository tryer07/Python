#定义一个函数，用于交换指定字典的key和value

#示例：给定字典{'a':1,'b':2,'c':3}，交换后输出{1:'a',2:'b',3:'c'}

#定义函数

def swap_key_value(input_dict: dict) -> dict:
    """
    该函数用于交换指定字典的key和value
    :param input_dict: 输入的字典
    :return: 交换key和value后的字典
    """

    #通过字典推导式遍历key和value并交换位置
    return {v: k for k, v in input_dict.items()}

#给定字典

original_dict = {'a': 1, 'b': 2, 'c': 3}

#调用函数

swapped_dict = swap_key_value(original_dict)

#打印结果

print(swapped_dict)