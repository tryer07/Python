#定义一个函数，该函数用于打印指定范围内所有的素数

#素数：一个大于1的自然数，除了1和它自身外，不能被其它自然数整除。

#用户输入区间起始值和结束值

start = int(input('请输入区间起始值：'))
end = int(input('请输入区间结束值：'))

#定义函数

#定义一个判断是否是素数的函数

def is_prime(num):
    """
    作用：判断一个数是否为素数
    :param num: 要判断的数
    :return: 如果是素数返回True，否则返回False
    """

    if num <=1:

        return False

    for i in range(2,num):
        if num % i == 0:
            return False

    return True

#定义一个打印素数的函数

def print_primes(start, end):
    """
    作用：打印指定范围内所有的素数
    :param start: 区间起始值
    :param end: 区间结束值
    """

    #遍历start到end

    for i in range(start,end + 1):
        if is_prime(i):
            print(f'该区间内{i}是素数')

print_primes(start, end)
