#编写一个程序，该程序将遍历用户指定区间内的所有整数，同时计算并输出整个遍历过程所消耗的总时间

#导入time模块

import time

#获取用户输入的区间

start = int(input('请输入区间开始值：'))

end = int(input('请输入区间结束值：'))

#定义变量保存循环开始时间（perf_counter 是单调高精度计时器，比 time.time() 更适合统计代码耗时）

start_time = time.perf_counter()

#定义变量保存遍历过程中的累加结果

total = 0

for i in range(start,end + 1):

    total += i  # 只计算不打印，避免控制台输出占据绝大部分耗时

#定义变量保存循环结束时间

end_time = time.perf_counter()

print('遍历过程所消耗的总时间：',end_time - start_time)