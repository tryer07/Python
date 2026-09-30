# 定义一个函数，该函数接收一个字典作为参数，返回键值交换后的新字典

# 定义函数
def swap_key_value(input_dict: dict) -> dict:
    """
    交换字典的键与值
    :param input_dict: 原字典
    :return: 键值交换后的新字典
    """
    # 使用字典推导式：把原来的 value 当作新 key，原来的 key 当作新 value
    return {v: k for k, v in input_dict.items()}


# 给定字典
original_dict = {'a': 1, 'b': 2, 'c': 3}

# 调用函数并打印结果
print(swap_key_value(original_dict))   # {1: 'a', 2: 'b', 3: 'c'}
