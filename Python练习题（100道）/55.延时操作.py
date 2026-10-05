#编写一个程序，该程序在暂停一秒后获取当前操作系统时间，并将其转换为'YYYY-MM-DD HH:MM:SS'格式的字符串进行打印

#导入time模块

import time

#获取当前系统时间(暂停前先打印输出)

local_time = time.localtime()

time_str = time.strftime('%Y-%m-%d %H:%M:%S',local_time)

print(time_str)

#将程序暂停执行指定的秒数(1秒)

time.sleep(1)

#获取当前系统时间(暂停后看输出是否延迟一秒)

local_time = time.localtime()

time_str = time.strftime('%Y-%m-%d %H:%M:%S',local_time)

print(time_str)