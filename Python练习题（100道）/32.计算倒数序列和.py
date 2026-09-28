#定义一个函数，该函数用于根据传入的整数n返回对应的倒数序列和，若n是奇数，则计算1/1 + 1/3 + ... + 1/n，若n是偶数，则计算1/2 + 1/4 + ... + 1/n

#用户输入数据
n = int(input('请填入n的值：'))

#定义函数

def sum_of_reciprocal_series(n):
    """
    计算并返回倒数序列和
    :param n: 正整数
    :return: 倒数序列和（float类型）
    """

    result = 0

    if n % 2 == 1:
        for i in range(1, n + 1, 2):
            result += 1 / i
    else:
        for i in range(2, n + 1, 2):
            result += 1 / i

    return result

#调用函数

result = sum_of_reciprocal_series(n)

print(result)
