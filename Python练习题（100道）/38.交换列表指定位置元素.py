# 定义一个函数，该函数用于将指定列表中指定索引位置的元素互换

# 定义函数
def swap_positions(newList, pos1, pos2):
    """
    交换列表中指定索引位置的两个元素
    :param newList: 列表
    :param pos1: 第一个元素的索引位置
    :param pos2: 第二个元素的索引位置
    :return: 交换后的列表
    """
    newList[pos1], newList[pos2] = newList[pos2], newList[pos1]
    return newList

# 交换列表元素
Li1 = [23, 65, 19, 90]

# 用户输入指定要交换的两个索引位置

pos1 = int(input("请输入第一个索引位置(选择数字0-3)："))
pos2 = int(input("请输入第二个索引位置(选择数字0-3)："))

# 调用函数
print(swap_positions(Li1, pos1, pos2))
