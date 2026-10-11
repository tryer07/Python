#定义一个简单的银行账户类，这个类支持简单的存取款操作

#定义银行账户类

class BankAccount:

    """用于模拟一个简单的银行账户，支持存款和取款操作"""

    def __init__(self,owner,balance = 0):

        #账户持有者

        self.owner = owner

        #账户余额，初始化为0

        self.balance = balance

    def deposit(self,amount):

        """
        执行存款操作
        :return: 存款金额
        """

        #判断要存入金额是否为正数

        if amount > 0:

            #累加到当前账户的余额中

            self.balance += amount
            return amount
        else:
            raise ValueError("存款金额必须为正数")

    def withdraw(self,amount):

        """
        执行取款操作
        :return: 取款金额
        """

        if amount > 0:

            #判断账户余额是否充足

            if self.balance >= amount:

                #从账户余额中减去取款金额

                self.balance -= amount
                return amount
            else:
                raise ValueError("余额不足")
        else:
            raise ValueError("取款金额必须为正数")

        def get_balance(self):

            """
            获取账户余额
            :param self: 账户对象
            :return: 账户余额
            :rtype: float
            """
            print("账户余额为：",self.balance)
            return self.balance

#示例使用

account = BankAccount("张三")
print(account.deposit(1000))
print(account.withdraw(500))
print(account.balance)
