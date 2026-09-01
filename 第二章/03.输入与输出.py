#输入与输出
#尝试1
# password1 = input('请输入暗号：')
# password2 = input('似乎还有呢：')
# print('暗号正确！')
# print('欢迎回家，主人！')

#尝试2(ATM取款)
total = 10000
password = input('请输入您的密码：')
num = input('请输入您需要取的金额：')
print(f'取款成功！您当前余额为：{total - int(num)}')
