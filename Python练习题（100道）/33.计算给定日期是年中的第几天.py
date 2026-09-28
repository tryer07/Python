#定义一个函数，该函数接收年月日作为参数，计算这一天是这一年的第几天

#接收用户输入

year = int(input("请输入年份："))
month = int(input("请输入月份："))
day = int(input("请输入日期："))


#定义函数

def is_leap_year(year):
    """
    判断给定的年份是否是闰年
    :param year: 年
    :return: 如果是闰年返回True，否则返回False
    """
    return year % 4 == 0 and year % 100 != 0 or year % 400 == 0

def day_of_year(year, month, day):
    """
    计算并返回给定日期是这一年的第几天
    :param year: 年
    :param month: 月
    :param day: 日
    """

    #定义变量保存平年每月的天数

    days_in_month = [31,28,31,30,31,30,31,31,30,31,30,31]

    #判断是否是闰年

    if is_leap_year(year):

        days_in_month[1] = 29

    #计算累计天数

    day_count = sum(days_in_month[:month - 1]) + day

    return day_count

print(f'给定日期是这一年的第{day_of_year(year, month, day)}天')
