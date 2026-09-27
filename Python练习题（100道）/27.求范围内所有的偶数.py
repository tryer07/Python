#定义一个函数，该函数用于返回指定范围内所有偶数的列表

#用户输入区间起始值和结束值

start = int(input('请输入区间起始值：'))
end = int(input('请输入区间结束值：'))

#定义函数

def get_even_numbers(start, end):
    """
    返回指定范围内所有偶数的列表
    :param start: 区间起始值
    :param end: 区间结束值
    :return: 指定范围内所有偶数的列表
    """
    #遍历start 至 end

    for i in range(start,end + 1):

        if i % 2 == 0:
            print(i)

#调用函数

get_even_numbers(start, end)
