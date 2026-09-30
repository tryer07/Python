#定义一个函数，该函数接收一个人的年龄作为参数，如果年龄不在正常范围内，则提示异常(小于0或者大于一百五)

#定义函数

def verify_age():
    """
    交互式获取并验证年龄：输入非整数或超出 0~150 范围都要求重新输入
    :return: 合法时返回年龄整数
    """
    while True:
        try:
            age = int(input('请输入您的年龄：'))
        except ValueError:
            print('输入错误，年龄必须是整数，请重新输入。')
            continue

        if age < 0 or age > 150:
            print('输入异常！年龄应在 0 到 150 之间，请重新输入。')
            continue

        return age


#调用函数

print(verify_age())


