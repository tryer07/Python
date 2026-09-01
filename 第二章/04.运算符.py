# 运算符号
#一.算术运算符计算优先级：括号 > **  >  *、/、//、%  >  +、-
# print(1 + 1)
# print(2 - 1)
# print(1 * 2)
# print(2 / 1)
# print(10 // 3)
# print(10 % 3)
# print(10 ** 3)
# print('0.1 + 10 / 4 ** 2',0.1 + 10 / 4 ** 2) #关于运算符优先级的展示，答案会是0.725，括号可以提高优先级，要优先运算某一部分可以使用括号。

#尝试1
# x = input('请输入x的值:')
# y = input('请输入y的值:')
# print('x + y = ',int(x) + int(y))
# print('x - y = ',int(x) - int(y))
#特别需要注意的是，这里的x和y在被int()转型之前都是字符串的形式，因此必须使用int()转型后才可以计算出正确结果。

#二.赋值运算符
# num = 85
# num += 10 #num = num + 10
# print(num) #95

# num -= 10 #num = num -10
# print(num) #85

# num *= 10 #num = num * 10
# print(num) #850

# num /= 10 #num = num / 10
# print(num) #85.0(从这里开始就是浮点数了，因为引入了整除)

# num %= 3 #num = num % 3
# print(num) #1.0

# num **= 3 #num = num **3
# print(num) #1.0

# num //= 10 #num = num //10
# print(num)
#有一个值得注意的点就是num的值是发生变化的，并不是每一次的计算都代入85进行每一次的运算，这里值得注意，还有整除后得到的数是浮点数，那么后面计算出来的结果都是浮点数

#比较运算符
# a == b   判断a是否等于b
# a != b   a不等于b
# a > b    a大于b
# a >= b   a大于等于b
# a < b    a小于b
# a <= b   a小于等于b
#这里比较出来的结果是布尔值
print('100 == 100?', 100 == 100) #True
print('100 != 100?', 100 != 100) #False
print('100 >= 100?', 100 >= 100) #True
print('100 <= 100?', 100 <= 100) #True

#逻辑运算符
#尝试1
# num = input('请输入一个整数:')
# n = int(num)
# if n >=10 and n<=20:
#     print('True')
# else:
#     print('False')

#尝试2
num = input('请输入一个整数：')
n = int(num)
if n <10 or n>20:
    print('True')
else:
    print('False')