#定义一个函数，该函数用于统计列表中元素出现次数

# 方法一：统计列表中指定元素出现的次数

#定义函数

def count_occurrences(lst, element):
    """
    统计列表中元素出现次数
    :param lst: 列表
    :param element: 元素
    :return: 元素在列表中出现的次数
    """

    count = 0
    for i in lst:
        if i == element:
            count += 1
    return count

#给定列表
Li = [1,4,3,3,2,2,3,5,3,1]

print(count_occurrences(Li, 3))

# 方法二：统计列表中所有元素出现的次数

# 定义函数
def count_all_occurrences(lst):
    """
    统计列表中所有元素出现的次数
    :param lst: 列表
    :return: 字典，键为元素，值为该元素出现的次数
    """
    result = {}
    for i in lst:
        # 元素第一次出现时 get 返回默认值 0，再 +1 累计
        result[i] = result.get(i, 0) + 1
    return result

# 给定列表
Li = [1, 4, 3, 3, 2, 2, 3, 5, 3, 1]

# 统计并展示所有元素出现的次数
counts = count_all_occurrences(Li)

for element, count in counts.items():
    print(f"元素 {element} 出现了 {count} 次")

# 方法三：统计列表中所有元素出现的次数（复用方法一）

def count_all_occurrences(lst):
    """
    统计列表中所有元素出现的次数
    :param lst: 列表
    :return: 字典，键为元素，值为该元素出现的次数
    """

    result = {}

    for element in set(lst):          # set 去重，遍历每个不同元素
        result[element] = count_occurrences(lst, element)   # 复用原函数

    return result

# 方法四：使用 collections.Counter 统计列表中所有元素出现的次数

# from collections import Counter

# def count_all_occurrences(lst):

#     return dict(Counter(lst))

# Li = [1, 4, 3, 3, 2, 2, 3, 5, 3, 1]

# print(count_all_occurrences(Li))   # {1: 2, 4: 1, 3: 4, 2: 2, 5: 1}