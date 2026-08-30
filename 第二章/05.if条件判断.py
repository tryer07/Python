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
admin = '18806092052'
password = 'wytlike688'
admin1 = '1839632447'
password1 = 'wytlike688'
a = input('请输入账号：')
b = input('请输入密码：')
if a == '18806092052' and b == 'wytlike688':
    print('登录成功！欢迎回来')
elif a == '1839632447' and b == 'wytlike688':
    print('登录成功！欢迎回来')
else:
    print('登录失败(悲)')