#编写一个程序，该程序将遍历并打印0-2999的所有整数，同时计算并输出整个遍历过程所消耗的总时间

#导入time模块

import time

#定义变量保存循环开始时间

start_time = time.time()

for i in range(0,3000):

    print(i)

#定义变量保存循环结束时间

end_time = time.time()

print('遍历过程所消耗的总时间：',end_time - start_time)
