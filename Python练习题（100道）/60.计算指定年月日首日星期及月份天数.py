#编写一个程序，计算并打印出指定年指定月份的第一天是星期几以及这个月份共有几天

#导入calendar模块

import calendar

#提示用户输入年份并将其转换为整型

year = int(input('请输入年份：'))

#提示用户输入月份并将其转换为整型

month = int(input('请输入月份：'))

#使用canlendar.monthrange()获取该月份的第一天是星期几以及这个月份有几天

weekday, monthrange = calendar.monthrange(year, month)

#注意这里返回星期几的索引中0才代表星期一，6代表星期日

#定义一个星期列表，将星期索引转换为对应的中文星期名称

weekdays = ['星期一','星期二','星期三','星期四','星期五','星期六','星期天']

print(f'该月份的第一天是',weekdays[weekday], '，这个月份有', monthrange, '天')