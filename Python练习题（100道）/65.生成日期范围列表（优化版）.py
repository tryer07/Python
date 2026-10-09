# 定义一个函数，它接收两个遵循'YYYY-MM-DD'格式的日期字符串参数begin_date和end_date。
# 该函数的任务是生成一个包含从begin_date到end_date(包括两端日期在内)所有日期的列表，并将该列表作为结果返回。

# 本版本在原始版本的基础上做了三点优化：
# 1. 用户可自由输入日期，不限于固定格式（借助 dateutil.parser 自动识别多种写法）；
# 2. 自动纠正开始/结束日期的先后顺序；
# 3. 每完成一次计算后，询问用户是否再进行一次计算。

# 导入datetime模块

import datetime

# 导入dateutil的parser模块，用于灵活解析多种日期输入格式

from dateutil import parser


# 定义一个函数

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


# 定义一个辅助函数：接收用户自由输入的日期字符串，
# 自动识别多种格式并统一返回标准的 YYYY-MM-DD 字符串；无法识别时返回 None

def parse_user_date(date_input):
    try:
        parsed_date_obj = parser.parse(date_input)
        return parsed_date_obj.strftime('%Y-%m-%d')
    except (ValueError, parser.parser.ParserError):
        return None


# 程序启动时先打印一段功能简介，让用户清楚这个程序是做什么的、以及需要如何配合输入

print("=" * 46)
print("            日期范围列表生成器")
print("=" * 46)
print("功能说明：本程序会根据您输入的【开始日期】和【结束日期】，")
print("          自动列出这两天之间（含首尾）的所有日期。")
print("使用提示：日期不必拘泥于固定格式，例如 2023-01-01、")
print("          2023/1/1、2023年1月1日、Jan 1 2023 等写法都能识别。")
print("=" * 46)

# 主循环：支持用户反复进行计算

while True:
    print("\n【第 1 步 / 共 2 步】请提供范围起点，也就是日期列表从哪一天开始：")
    while True:
        begin_input = input(">>> 请输入开始日期：").strip()
        begin_date = parse_user_date(begin_input)
        if begin_date is not None:
            break
        print("    无法识别该日期，请重新输入一个有效的日期！")

    print("\n【第 2 步 / 共 2 步】请提供范围终点，也就是日期列表到哪一天结束：")
    while True:
        end_input = input(">>> 请输入结束日期：").strip()
        end_date = parse_user_date(end_input)
        if end_date is not None:
            break
        print("    无法识别该日期，请重新输入一个有效的日期！")

    # 若开始日期晚于结束日期，自动交换两者，保证范围有效

    if begin_date > end_date:
        begin_date, end_date = end_date, begin_date
        print("注意：您输入的开始日期晚于结束日期，已自动调整为从早到晚的顺序。")

    # 调用函数生成日期范围并整齐输出结果

    date_range = get_date_range(begin_date, end_date)
    print(f"\n计算结果 —— 从 {begin_date} 到 {end_date} 的日期范围列表（共 {len(date_range)} 天）：")
    print("-" * 40)
    for index, date_str in enumerate(date_range, start=1):
        print(f"  {index:>2}. {date_str}")

    # 计算完成后询问用户是否再进行一次计算

    again = input("\n是否再进行一次计算？(输入 y 继续 / 其他任意键结束)：").strip().lower()
    if again != 'y':
        print("感谢使用，程序已结束！")
        break