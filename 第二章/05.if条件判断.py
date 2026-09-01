#if语句
#尝试1
# score = input('请输入你的高考成绩:')
# a = int(score)
# if a >=680:
#     print('清华北大欢迎你')
# elif 600 <= a < 680:
#     print('985 211我来啦！')
# elif 500 <= a <600:
#     print('好的本科不比大专差')
# else:
#     print('进厂进厂')

#尝试2
# admin ='123456'
# password = '123'
# a = input('请输入账号：')
# b = input('请输入密码：')
#
# if a==admin and b==password:
#     print('登录成功！欢迎回来：古调独弹')
# else:
#     print('账号或密码错误，登录失败(悲)')

#尝试3
# year = int(input('请输入需要判断的年份：'))
# if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0:
#     print('今年是闰年')
# else:
#     print('今年是平年')

#练习1
# age = int(input('请输入您的年龄：'))
# if age % 2 == 0:
#     print('您的年龄是偶数')
# else:
#     print('您的年龄是奇数')

#练习2
# age = int(input('请输入您的年龄'))
# if age >=18:
#     print('成年人:')
# else:
#     print('未成年')

#练习3
# num = int(input('请输入一个数字：'))
# if num > 0:
#     print('这个数是正数')
# elif num < 0:
#     print('这个数是负数')
# else:
#     print('这个数是0')

#练习4
# admin = '18806092052'
# password = 'wytlike688'
# admin1 = '1839632447'
# password1 = 'wytlike688'
# a = input('请输入账号：')
# b = input('请输入密码：')
# if a == '18806092052' and b == 'wytlike688':
#     print('登录成功！欢迎回来')
# elif a == '1839632447' and b == 'wytlike688':
#     print('登录成功！欢迎回来')
# else:
#     print('登录失败(悲)')

#练习5
# a = int(input('请输入边长1：'))
# b = int(input('请输入边长2：'))
# c = int(input('请输入边长3：'))
# if a + b > c and b + c > a and c + a > b:
#     if a == b == c:
#         print('这个三角形是等边三角形')
#     elif a == b or b == c or a == c:
#         print('这个三角形是等腰三角形')
#     else:
#         print('这是一个普通的三角形')
# else:
#     print('这三个边长不构成三角形哦')

#练习6
# day = int(input('请输入今天周几：'))
# if day == 1 or day == 2 or day == 3 or day == 4 or day == 5:
#     print('好好上班吧，牛马')
# elif day == 6 or day == 7:
#     print('劳资明天不上班')
# else:
#     print('输入错误！')

day = int(input('请输入今天周几：'))
if day == 1:
    print('学习')
elif day == 2:
    print('出差')
elif day == 3:
    print('开会')
elif day == 4:
    print('项目报告')
elif day == 5:
    print('周总结')
elif day == 6 or day == 7:
    print('周末休息')
else:
    print('输入错误')