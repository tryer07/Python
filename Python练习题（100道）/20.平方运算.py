#持续提示用户输入一个数字，并对该数字的平方进行运算，如果平方运算的结果小于50，则停止输入

while True:
    num = int(input('请输入一个数字(直到这个数的平方小于50为止)：'))

    result = num ** 2

    if result >= 50:
        print('平方运算结果为：',result)

    elif result < 50:
        print('平方运算结果为：',result)
        break

    else:
        print('输入无效！')

