#定义一个函数，它接收两个遵循'YYYY-MM-DD'格式的日期字符串参数begin_date和end_date。该函数的任务是生成一个包含从begin_date到end_date(包括两端日期在内)所有日期的列表，并将该列表作为结果返回。

#导入模块

import datetime

#定义一个函数

def get_date_range(begin_date, end_date):
    """
    生成一个包含从begin_date到end_date(包括两端日期在内)所有日期的列表

    参数：
    begin_date (str): 开始日期，格式为'YYYY-MM-DD'
    end_date (str): 结束日期，格式为'YYYY-MM-DD'

    返回：
    list: 包含从begin_date到end_date(包括两端日期在内)所有日期的列表
    """
    date_range = []
    begin_date_obj = datetime.datetime.strptime(begin_date, '%Y-%m-%d')
    end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    current_date = begin_date_obj
    while current_date <= end_date_obj:
        date_range.append(current_date.strftime('%Y-%m-%d'))
        current_date += datetime.timedelta(days=1)
    return date_range

#测试函数

date_range = get_date_range('2023-01-01', '2023-01-10')

print(date_range)

