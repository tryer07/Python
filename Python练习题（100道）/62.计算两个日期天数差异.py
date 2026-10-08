#编写一个程序，用于计算两个日期之间天数的差异

#导入datetime模块

import datetime

#用户输入第一个日期

datetime1 = datetime.datetime.strptime(input('请输入第一个日期(输入格式为YYYY-MM-DD)：'), '%Y-%m-%d')

#用户输入第二个日期

datetime2 = datetime.datetime.strptime(input('请输入第二个日期(输入格式为YYYY-MM-DD)：'), '%Y-%m-%d')

#计算两个日期之间天数的差异

difference = datetime2 - datetime1

difference = difference.days

print('两个日期之间天数的差异为：', difference, '天')
