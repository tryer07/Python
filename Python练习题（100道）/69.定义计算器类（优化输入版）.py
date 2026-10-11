#定义一个简单的计算器，这个类支持加、减、乘、除四种基本运算
#（优化输入版：用户自主输入数字与运算形式，运算结束后可选择继续）

#定义计算器类

class Calculate:

    """
    定义一个简单的计算器，这个类支持加、减、乘、除四种基本运算
    """

    #定义函数

    @staticmethod
    def add(a,b):
        """
        加法
        :param a: 加数
        :param b: 加数
        :return: 和
        """
        return a + b

    @staticmethod
    def subtract(a,b):
        """
        减法
        :param a: 被减数
        :param b: 减数
        :return: 差
        """
        return a - b

    @staticmethod
    def multiply(a,b):
        """
        乘法
        :param a: 乘数
        :param b: 乘数
        :return: 积
        """
        return a * b

    @staticmethod
    def divide(a,b):
        """
        除法
        :param a: 被除数
        :param b: 除数
        :return: 商
        """

        if b == 0:
            raise ValueError("除数不能为零")

        return a / b

#辅助函数：读取一个数字（带输入校验）

def read_number(prompt):
    """
    反复提示用户输入，直到输入的是一个合法数字为止
    :param prompt: 输入提示信息
    :return: 转换后的数字（float）
    """

    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("输入无效，请输入一个数字。")

#辅助函数：读取一个运算选择（1~4）

def read_choice():
    """
    反复提示用户输入，直到选择一个合法的运算编号为止
    :return: 运算编号（1、2、3、4）
    """

    while True:
        choice = input("请选择运算形式（1:加法 2:减法 3:乘法 4:除法）：").strip()
        if choice in ("1", "2", "3", "4"):
            return choice
        print("输入无效，请输入 1 ~ 4 之间的数字。")

#主程序

calc = Calculate()

while True:

    choice = read_choice()

    a = read_number("请输入第一个数字：")
    b = read_number("请输入第二个数字：")

    #根据用户选择的运算形式调用对应方法并输出结果
    if choice == "1":
        print(f"加法：{a} + {b} = {calc.add(a, b)}")
    elif choice == "2":
        print(f"减法：{a} - {b} = {calc.subtract(a, b)}")
    elif choice == "3":
        print(f"乘法：{a} × {b} = {calc.multiply(a, b)}")
    else:
        #除法需处理除数为零的异常
        try:
            print(f"除法：{a} ÷ {b} = {calc.divide(a, b):.2f}")
        except ValueError as e:
            print(f"计算失败：{e}")

    #运算结束后询问用户是否再次进行运算
    again = input("是否继续进行运算？（y/n）：").strip().lower()
    if again != "y":
        print("感谢使用，计算器已退出。")
        break