#编写一个程序，给定一个Unix时间戳(例如：1620747224)，请将其转换成对应的日期和时间字符串，格式为'YYYY-MM-DD HH:MM:SS'。

#导入datetime模块

import datetime

#给定Unix时间戳(从1970-01-01 00:00:00以来开始计算的UTC秒数)

Unix_time = 1620747224

#使用datetime.datetime.fromtimestamp()将Unix时间戳转换为datetime对象

datetime_object = datetime.datetime.fromtimestamp(Unix_time)

print(datetime_object,type(datetime_object))

#将datetime对象转换为指定格式的字符串

datetime_str = datetime_object.strftime('%Y-%m-%d %H:%M:%S')

print(datetime_str,type(datetime_str))
