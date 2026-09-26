#编写一个程序，计算n + nn + ... + n个n的值，其中n是数字，且加数的个数有键盘输入决定

#获取用户输入数据

n = int(input('请输入一个数字：'))

count = int(input('请输入这个数字需要相加的项数：'))

#定义变量保存初始值

current_term = 0

#定义变量保存结果

result = 0

#循环生成每一项并累加每一项

for i in range(1,count + 1):

    current_term = current_term * 10 + n

    result += current_term

print('结果为：',result)




