#定义一个函数，该函数用于尝试将用户输入的字符串转化成整数，如果转换成功，则返回整数，如果转换失败，则返回错误信息

#定义函数

def string_to_int():
    """
    该函数用于尝试将用户输入的字符串转化成整数，如果转换成功，则返回整数，如果转换失败，则返回错误信息
    :return: 整数或错误信息
    """

    while True:
        try:

            # 接收用户输入信息

            num = int(input('请输入一个整数：'))
            return num          # 转换成功，返回整数并结束函数

        except ValueError:
            # 转换失败：只提示，不 return，循环会自动进入下一轮重新询问
            print('输入错误，请输入一个有效的整数。')
            continue


#调用函数

print(string_to_int())



