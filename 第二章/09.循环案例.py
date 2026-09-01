#根据输入的账号和密码执行有关登录的操作，具体要求如下：
#1.设定正确的账号和密码
#2.输入正确的账号和密码则登录成功，输入错误的则继续输入直到正确为止
#3.输入的账号和密码不能为空

while True:

    username = input('请输入用户账号：')
    password = input('请输入用户密码：')

    if username == '' or password == '':
        print('输入的账号或密码不得为空！')
        continue

    if username == '1839632447' and password == 'wytlike688':
        print('登录成功！')
        break
    elif username == '18806092052' and password == 'wytlike688':
        print('登录成功！')
        break
    else:
        print('用户名或者密码输入错误，请重新输入：')
