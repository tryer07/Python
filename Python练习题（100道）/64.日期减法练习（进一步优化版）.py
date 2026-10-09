# 定义一个函数，该函数接收两个参数：一个遵循'YYYY-MM-DD'格式的日期字符串pdate以及一个整数days。
# 该函数的任务是计算出从给定日期向前days天后的新日期

# 本版本在“优化版”的基础上，进一步放宽了日期输入的要求：
# 借助 dateutil.parser 自动识别多种日期写法（例如 2023-04-01、2023/4/1、2023年4月1日、
# Apr 1 2023、04-01-2023 等），用户不必严格按照固定格式输入也能完成计算。

# 导入datetime模块

import datetime

# 导入dateutil的parser模块，用于灵活解析多种日期输入格式

from dateutil import parser


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


# 输入日期：使用 dateutil.parser 自动识别多种格式，
# 解析成功后统一转换成标准的 YYYY-MM-DD 字符串，无法识别时提示重新输入

while True:
    date_input = input("请输入一个日期（支持多种写法，例如 2023-04-01、2023/4/1、2023年4月1日、Apr 1 2023）：").strip()
    try:
        parsed_date_obj = parser.parse(date_input)
        original_date = parsed_date_obj.strftime('%Y-%m-%d')
        break
    except (ValueError, parser.parser.ParserError):
        print("无法识别该日期，请重新输入一个有效的日期！")

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
