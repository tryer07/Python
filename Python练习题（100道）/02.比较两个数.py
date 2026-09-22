#定义两个整形变量，比较它们的值并打印结果

#定义两个整型变量

a:int = int(input('请为a赋值：'))
b:int = int(input('请为b赋值：'))

#比较两个数的大小并打印结果

if a > b:
    print('a大于b')
elif a < b:
    print('a小于b')
else:
    print('a等于b')
