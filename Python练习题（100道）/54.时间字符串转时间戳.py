#给定一个表示时间的字符串，要求将其转化为以秒为单位的整数时间戳

#导入time模块

import time

#时间字符串(格式1)

a1 = '2025-4-10 23:40:00'

#使用time.strptime()将时间字符串转换为时间数组(步骤1)

time_array = time.strptime(a1, '%Y-%m-%d %H:%M:%S')

print(time_array)

#使用time.mktime()将时间数组转换为时间戳(步骤2)

timestamp = int(time.mktime(time_array))

print(timestamp)

#时间字符串(格式2)

a2 = '2025/4/10 23:40:00'

#格式同上，修改占位符格式-为/即可

time_array = time.strptime(a2, '%Y/%m/%d %H:%M:%S')

print(time_array)

timestamp = int(time.mktime(time_array))

print(timestamp)
