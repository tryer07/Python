#编写一个程序，要求用户输入年份和月份，打印该月份对应的日历

#导入日历模块 calendar

import calendar

#提示用户输入年份并将其转换为整型

year = int(input('请输入年份：'))

#提示用户输入月份并将其转换为整型

month = int(input('请输入月份：'))

print(calendar.month(year, month))
