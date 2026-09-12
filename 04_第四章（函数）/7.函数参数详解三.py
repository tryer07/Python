#不定长参数

#类型一：

#定义函数
#注意*args仅封装传递位置参数，不封装传递关键字参数

def calc_data(*args): #注意这里的args是约定俗成，并不是关键字，输入其它的例如：*data也是可以的
    """
    根据传入的数据计算传入数据的最大值最小值和平均值
    :param args: 不定长位置参数
    :return: 返回输入数据的最大值最小值和平均值
    """
    max_data = max(args)
    min_data = min(args)
    avg_data = round(sum(args) / len(args),2)
    return max_data, min_data, round(avg_data,2)

#调用函数

print(calc_data(1,2,3,4,5,6,7,8,9,10))


#类型二：关键字传递

def calc_data(*args,**kwargs): #注意这里的kwargs也是约定俗成，并不是关键字，输入其它的例如：**data也是可以的
    """
    根据传入的数据计算其最大值最小值和平均值
    :param args:不定长位置参数
    :param kwargs:不定长关键字参数
    :return:返回
    :round:保留的小数位数
    :print:是否打印输出
    """

    max_data = max(args)
    min_data = min(args)
    avg_data = sum(args) / len(args)

    if kwargs.get('round') is not None:
        avg_data = round(sum(args) / len(args),2)
    if kwargs.get('print') :
        print(f'计算出来的最大值：{max_data},最小值：{min_data},平均值：{avg_data}')

    return max_data, min_data, avg_data

#调用函数

print(calc_data(1,2,3,4,5,6,7,8,9,10,round = 2,print=True)) #这个代码中的数字会封装到*args这个位置参数中，round和print则会封装到**kwargs这个关键字参数中
(calc_data(1,2,3,4,5,6,7,8,9,10,round = 2,print=True))


