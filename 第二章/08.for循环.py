#for循环
# msg = input('请输入需要遍历的字符串：')
# for i in msg:
#     print(i)
# else:
#     print('循环结束')

#接下来是用for语句完成while同样的功能
#用for语句计算1-100的奇数和
# total = 0
# for i in range(1,101):
#     if i % 2 == 1:
#         total += i
#     print('1-100的奇数和：',total)

#简化版本代码
# total = 0
# for i in range(1,101,2):
#     total += i
#     print('1-100的奇数和：',total)

#用for语句计算100-500之间3的倍数的数的和
# total = 0
# for i in range(100,501):
#     if i % 3 == 0:
#         total += i
#     print('100-500之间3的倍数的数的和：',total)

#嵌套for循环
#打印一个长度为m，宽度为n的长方形
# m = int(input('请输入长方形的长度：'))
# n = int(input('请输入长方形的宽度：'))
# for j in range(n):
#     for i in range(m):
#         print('*', end='  ')
#     print()

# m = int(input('请输入长方形的长度：'))
# n = int(input('请输入长方形的宽度：'))
# for i in range(m):
#     for j in range(n):
#         print('*', end='  ')
#     print()

#打印99乘法表
for i in range(1,10):
    for j in range(1,i+1):
        print(f'{i}×{j}={i*j}',end='\t')
    print()