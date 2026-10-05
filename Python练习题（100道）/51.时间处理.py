#编写一个程序，使用time模块来实现时间处理功能

#导入time模块，用于处理时间相关的任务

import time

#获取当前时间的时间戳，即自1970-01-01 00:00:00以来的秒数

current_timestamp = time.time()

print(current_timestamp)

#将时间戳转换为本地时间的字符串。若没有指定参数，则默认当前时间戳

#获取当前时间的字符串表示

current_time_str1 = time.ctime()

print(current_time_str1)

#获取指定时间的字符串表示

specified_time_str = time.ctime(1717102524)

print(specified_time_str)

#将时间戳转化为本地时间的struct_time对象(年月日时分秒等)。若没有指定参数，则默认当前时间戳

#获取当前时间的struct_time对象

current_local_time = time.localtime()

print(current_local_time)

#获取指定时间的struct_time对象

specified_local_time = time.localtime(1617102524)

print(specified_local_time)

#将时间戳转化为UTC时间的struct_time对象。若没有指定参数，则默认当前时间戳

#获取当前时间的UTC时间的struct_time对象

current_utc_time = time.gmtime()

print(current_utc_time)

#获取指定时间的UTC时间的struct_time对象

specified_utc_time = time.gmtime(1617102524)

print(specified_utc_time)

#将struct_time转化为特定格式的字符串表示(格式为：年-月-日 时:分:秒)

local_formatted_time_string = time.asctime(time.localtime())

print(local_formatted_time_string)
