#编写一个程序，解析给定的日期字符串“Aug 28 2025 8:00 AM”，并打印出解析后的日期时间对象

#导入模块(用于实现日期字符串解析)

from dateutil import parser

#给定日期字符串

date_string = 'Aug 28 2025 8:00 AM'

#将日期字符串解析为日期时间对象

parsed_date = parser.parse(date_string)

#打印解析后的日期时间对象

print(parsed_date)