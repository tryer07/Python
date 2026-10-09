# 定义一个函数，该函数接收两个参数：一个遵循'YYYY-MM-DD'格式的日期字符串pdate以及一个整数days。
# 该函数的任务是计算出从给定日期向前days天后的新日期

# 导入datetime模块

import datetime


# 定义函数

def calculate_previous_date(pdate, days):
    """
    计算从给定日期向前days天后的日期
    :param pdate: 遵循'YYYY-MM-DD'格式的日期字符串
    :param days: 整数，表示天数
    :return: 从给定日期向前days天后的日期字符串，遵循'YYYY-MM-DD'格式
    """
    pdate_obj = datetime.datetime.strptime(pdate, '%Y-%m-%d')
    time_gap = datetime.timedelta(days=days)
    new_date = pdate_obj - time_gap
    return new_date.strftime('%Y-%m-%d')


# 输入日期，并校验格式是否正确（YYYY-MM-DD）

while True:
    original_date = input("请输入一个日期（格式：YYYY-MM-DD，例如 2023-04-01）：").strip()
    try:
        datetime.datetime.strptime(original_date, '%Y-%m-%d')
        break
    except ValueError:
        print("日期格式不正确，请按照 YYYY-MM-DD 的格式重新输入！")

# 输入要往前推的天数，并校验是否为正整数

while True:
    days_input = input("请输入要往前推的天数（正整数）：").strip()
    try:
        days = int(days_input)
        if days < 0:
            print("天数不能为负数，请重新输入！")
            continue
        break
    except ValueError:
        print("输入无效，请输入一个整数！")

# 调用函数并输出结果

result_date = calculate_previous_date(original_date, days)
print(f"从 {original_date} 往前推 {days} 天后的日期是：{result_date}")
