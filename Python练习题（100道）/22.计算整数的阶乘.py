#定义一个名为factorial的函数，该函数用于计算并返回给定整数的阶乘

#用户输入一个非负整数

number = int(input('请输入一个非负整数：'))

#定义函数

def factorial(number):
    """
    作用：计算并返回给定整数的阶乘

    参数：number(非负整数)

    :return:给定的整数的阶乘值
    """

    #定义变量保存初始值

    result = 1

    #遍历1到number

    for i in range(1,number + 1):

        result *= i

    return result

factorial(number)

print(factorial(number))
