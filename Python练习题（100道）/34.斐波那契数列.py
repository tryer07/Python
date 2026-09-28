#定义一个函数，该函数用于计算斐波那契数列中的第n项

#用户输入数据

n = int(input('请输入项数：'))

#定义函数

def fibonacci(n):
    """
    计算并返回斐波那契数列中的第n项
    :param n: 正整数
    :return: 斐波那契数列中的第n项
    """

    if n <= 0:
        print('项数必须是正整数！')
        return None

    elif n == 1 or n == 2:
        return 1

    a, b = 1, 1
    for i in range(3, n + 1):
        a, b = b, a + b

    return b

#调用函数并接收返回值

result = fibonacci(n)

if result is not None:

    print(f'斐波那契数列第{n}项的值为：{result}')

