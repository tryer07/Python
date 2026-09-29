# 定义一个函数，该函数接收一个正整数参数rows，其功能是打印出一个由星号 * 组成的、具有rows指定行数的菱形图案


# 定义函数
def print_rhombus(rows):
    """
    打印菱形
    :param rows: 正整数
    :return: 打印成功返回 True；行数为偶数（非法）返回 False
    """

    # 判断rows是否为偶数
    if rows % 2 == 0:
        print('行数必须是奇数！')
        return False

    # 打印上半部分（不含中间行）
    for i in range(1, rows, 2):
        # 前导空格
        space = ' ' * ((rows - i) // 2)
        # 星号
        star = '*' * i
        # 打印
        print(space + star)

    # 打印下半部分（含中间行）
    for i in range(rows, 0, -2):
        # 前导空格
        space = ' ' * ((rows - i) // 2)
        # 星号
        star = '*' * i
        # 打印
        print(space + star)

    return True


# 用 while True 循环校验输入：输入偶数则重新提示，直到输入合法奇数为止
while True:
    # 用户输入所需要打印的行数
    rows = int(input("请输入行数："))

    # 调用函数：打印成功（返回 True）就退出循环，否则继续重新输入
    if print_rhombus(rows):
        break


