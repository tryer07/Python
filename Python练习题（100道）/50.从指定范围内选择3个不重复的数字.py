#编写一个程序，该程序能从用户指定的范围内获取3个随机不重复的数字

#导入模块

import random

#用户指定范围

start = int(input('请输入您所需要的起始区间：'))

end = int(input('请输入您所需要的结束区间：'))

#使用random,sample(population,k)完成需求，这个语句的意思是从population序列中随机选择k个不重复的元素

result = random.sample(range(start,end + 1),3)

print(f'为您选择的3个不重复的随机数字分别是：{result}')