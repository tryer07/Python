#定义一个函数，该函数接收两个参数：一个遵循‘YYYY-MM-DD’格式的日期字符串pdate以及一个整数days。该函数的任务是计算出从给定日期向前days后的新日期

#导入datetime模块

import datetime

#定义函数

def calculate_previous_date(pdate, days):
    """
    计算从给定日期向前days后的日期
    :param pdate: 遵循'YYYY-MM-DD'格式的日期字符串
    :param days: 整数，表示天数
    :return: 从给定日期向前days后的日期字符串，遵循'YYYY-MM-DD'格式
    """
    pdate_obj = datetime.datetime.strptime(pdate, '%Y-%m-%d')
    time_gap = datetime.timedelta(days=days)
    new_date = pdate_obj - time_gap
    return new_date.strftime('%Y-%m-%d')

#调用函数并接收返回值

original_date = '2023-04-01'
days = 5
result_date = calculate_previous_date(original_date, days)
print(f"从 {original_date} 往前推 {days} 天后的日期是：{result_date}")

