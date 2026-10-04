#编写一个程序，该程序能够根据用户指定的长度生成一个验证码(可包含大小写英文字母以及数字)

#导入模块

import random
import string

#获取用户输入信息

lens = int(input('请输入你想要验证码的长度：'))

#定义验证码中可能包含的字符集(需要导入string模块)

chars = string.digits + string.ascii_letters

verify_code = ''

for i in range(lens):

    verify_code += random.choice(chars)

print(f'本次生成的验证码是：{verify_code}')

