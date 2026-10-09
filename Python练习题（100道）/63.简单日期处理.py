#编写一个程序，使用datetime模块完成以下任务：
#1.输出今日日期(YYYY-MM-DD格式)
#2.创建并输出宫崎骏生日的日期(1941年1月5日)
#3.计算并输出宫崎骏生日的下一天
#4.计算并输出宫崎骏的一岁生日日期

#导入datetime模块

import datetime

#1.输出今日日期

print(datetime.datetime.now().strftime('%Y-%m-%d'))

#2.创建并输出宫崎骏生日的日期(1941年1月5日)，使用datetime.datetime(year, month, day)创建日期对象

birthday = datetime.datetime(1941, 1, 5)

print(birthday.strftime('%Y-%m-%d'))

#3.计算并输出宫崎骏生日的下一天

next_day = birthday + datetime.timedelta(days=1)

print(next_day.strftime('%Y-%m-%d'))

#4.计算并输出宫崎骏的一岁生日日期

one_year_birthday = birthday + datetime.timedelta(days=365)

print(one_year_birthday.strftime('%Y-%m-%d'))
