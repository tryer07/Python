#定义一个函数，该函数接收一个正整数n作为参数，并将其分解为质因数，打印分解结果

#例如：90 = 2 * 3 * 3 * 5

#定义函数

def prime_factorization(n):
    """
    分解质因数
    作用：将正整数n分解为质因数，并打印分解结果，例如90 = 2 * 3 * 3 * 5
    :param n: 正整数
    :return: None
    """

    #处理n为1的情况

    if n == 1:

        print('1 = 1')

        return None

    #处理n大于等于2的情况

    original_n = n
    factors = []
    divisor = 2

    while n > 1:
        while n % divisor == 0:
            factors.append(divisor)
            n = n // divisor
        divisor += 1

    result_str = ' * '.join(str(f) for f in factors)
    print(f'{original_n} = {result_str}')
    return None


#用户输入数据

num = int(input('请输入一个正整数：'))

#调用函数

prime_factorization(num)

