#编写一个程序，用于计算两个日期之间天数的差异（优化版）
#优化点：
#1.放宽输入格式，支持多种常见写法（如 2024-01-05 / 2024/1/5 / 2024.1.5 / 20240105）
#2.输入错误不会报错崩溃，而是提示后让用户重新输入

#导入datetime模块

import datetime

#定义支持的日期格式列表，程序会依次尝试，命中任意一个即视为输入合法

DATE_FORMATS = [
    '%Y-%m-%d',     # 2024-01-05
    '%Y/%m/%d',     # 2024/1/5
    '%Y.%m.%d',     # 2024.1.5
    '%Y%m%d',       # 20240105
    '%Y年%m月%d日',  # 2024年1月5日
]

#封装一个"读取并解析日期"的函数，输入非法时会循环提示，直到拿到合法日期为止

def input_date(prompt):
    while True:
        #先读取原始字符串，并去除首尾空格，避免误输入的空格导致解析失败
        date_str = input(prompt).strip()
        #依次尝试每一种格式，只要有一种能解析成功就返回日期对象
        for fmt in DATE_FORMATS:
            try:
                return datetime.datetime.strptime(date_str, fmt)
            except ValueError:
                #当前格式不匹配，换下一个格式继续尝试
                continue
        #所有格式都尝试失败，说明输入确实不合法，打印提示后让while循环进入下一轮重输
        print(f'  -> 输入的日期「{date_str}」无法识别，请重新输入（例如：2024-01-05）')

#用户输入第一个日期

datetime1 = input_date('请输入第一个日期：')

#用户输入第二个日期

datetime2 = input_date('请输入第二个日期：')

#计算两个日期之间天数的差异

difference = (datetime2 - datetime1).days

print('两个日期之间天数的差异为：', abs(difference), '天')
