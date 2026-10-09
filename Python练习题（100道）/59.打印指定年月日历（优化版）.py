# 编写一个程序，要求用户输入年份和月份，打印该月份对应的日历（优化版）
# 优化点1：输入验证——非整数、越界年份/月份都不再崩溃，而是重新提示输入
# 优化点2：支持连续查询——打印完日历后可选择继续查询或退出程序

# 导入日历模块

import calendar

# 定义函数：反复询问直到用户输入一个合法整数（沿用43题 while True + try/except 模式）

def get_int(prompt):
    """
    获取用户输入并验证是否为整数
    :param prompt: 提示文字
    :return: 合法整数
    """
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print('输入错误，请输入一个整数。')

# 定义函数：获取年份，并检查合理范围

def get_year():
    while True:
        year = get_int('请输入年份（如 2026）：')
        if 1 <= year <= 9999:      # calendar 模块只支持有效年份，越界会报错
            return year
        print('年份越界，请输入 1 到 9999 之间的年份。')

# 定义函数：获取月份，并检查 1-12 范围（修复原版输 13 直接崩溃的缺陷）

def get_month():
    while True:
        month = get_int('请输入月份（1-12）：')
        if 1 <= month <= 12:
            return month
        print('月份应在 1 到 12 之间，请重新输入。')

# 外层循环支撑多次查询（沿用56优化版的菜单常驻模式）

while True:

    year = get_year()
    month = get_month()

    print(calendar.month(year, month))

    choice = input('是否继续查询其他月份？（按 y 继续 / 按 n 结束）：')
    if choice.lower() != 'y':
        break

print('感谢使用，再见！')