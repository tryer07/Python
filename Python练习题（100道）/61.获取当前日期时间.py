#编写一个程序，用于获取并显示当前日期和时间

#导入datetime模块，用于处理日期和时间相关的任务

import datetime

#为了完成该需求，可以使用datetime.datetime.now()获取当前本地日期时间，包含年、月、日、时、分、秒和微秒

current_datetime = datetime.datetime.now()

print(current_datetime)

print(type(current_datetime))

#使用strftime()将日期时间对象转换为特定格式输出

time_str = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

print(time_str)

#分别打印年、月、日、时、分、秒

print('年：',current_datetime.year)
print('月：',current_datetime.month)
print('日：',current_datetime.day)
print('时：',current_datetime.hour)
print('分：',current_datetime.minute)
print('秒：',current_datetime.second)
