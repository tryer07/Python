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

#调用函数并接收返回的日期范围列表

begin_date = '2023-01-01'
end_date = '2023-01-10'
date_range = get_date_range(begin_date, end_date)

#输出结果：先打印标题与总数，再逐行整齐地列出每个日期

print(f"从 {begin_date} 到 {end_date} 的日期范围列表（共 {len(date_range)} 天）：")
print("-" * 40)
for index, date_str in enumerate(date_range, start=1):
    print(f"  {index:>2}. {date_str}")

