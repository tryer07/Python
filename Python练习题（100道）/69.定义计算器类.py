#定义一个简单的计算器，这个类支持加、减、乘、除四种基本运算

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

#示例使用

calc = Calculate()

a, b = 5, 3

print(f"加法：{a} + {b} = {calc.add(a, b)}")
print(f"减法：{a} - {b} = {calc.subtract(a, b)}")
print(f"乘法：{a} × {b} = {calc.multiply(a, b)}")
print(f"除法：{a} ÷ {b} = {calc.divide(a, b):.2f}")
