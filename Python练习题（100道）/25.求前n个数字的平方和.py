#定义一个函数，求前n个数字的平方和

#用户输入一个正整数

n = int(input('请输入一个正整数：'))

#定义函数

def sum_of_square(n):
    """
    作用：求前n个数字的平方和
    :param n: 正整数
    :return: 前n个数字的平方和
    """

    #遍历1到n

    result = 0

    for i in range(1,n + 1):

        result = result +  i ** 2

    return result

print('前',n,'个数字的平方和为：',sum_of_square(n))

