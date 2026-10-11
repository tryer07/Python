# 定义一个简单的银行账户类，支持登录校验与存款、取款、查询余额操作（优化版）
# 优化点：
# 1. 账户增加账号、密码，执行任何操作前需先登录验证
# 2. 菜单式交互，用户可自由选择 存款 / 取款 / 查询余额 / 退出
# 3. 金额输入统一校验，输错不会崩溃，而是重新提示
# 4. 修复原版 get_balance 被错误缩进在 withdraw 内部、无法从外部调用的缺陷


class BankAccount:

    """模拟一个简单的银行账户，支持登录、存款、取款和查询余额"""

    def __init__(self, owner, account_number, password, balance=0):

        # 账户持有者
        self.owner = owner

        # 账号（用于登录校验）
        self.account_number = account_number

        # 密码（用于登录校验）
        self.password = password

        # 账户余额，默认余额一千万由创建时传入
        self.balance = balance

    def verify(self, account_number, password):

        """校验输入的账号与密码是否都正确，正确返回 True"""

        return (account_number == self.account_number
                and password == self.password)

    def deposit(self, amount):

        """
        执行存款操作
        :param amount: 存款金额，必须为正数
        :return: 实际存入的金额
        """

        if amount > 0:
            # 累加到当前账户的余额中
            self.balance += amount
            return amount
        else:
            raise ValueError("存款金额必须为正数")

    def withdraw(self, amount):

        """
        执行取款操作
        :param amount: 取款金额，必须为正数且不超过余额
        :return: 实际取出的金额
        """

        if amount > 0:
            # 判断账户余额是否充足
            if self.balance >= amount:
                # 从账户余额中减去取款金额
                self.balance -= amount
                return amount
            else:
                raise ValueError("余额不足")
        else:
            raise ValueError("取款金额必须为正数")

    def get_balance(self):

        """
        获取账户当前余额
        :return: 账户余额
        """

        return self.balance


def get_amount(prompt):

    """
    反复询问直到用户输入一个大于 0 的金额（标志位循环 + 循环外统一返回，规避 PyCharm 对 while True 的隐式 None 误判）
    :param prompt: 提示文字
    :return: 合法金额（浮点数）
    """

    # 初始化结果变量与标志位，保证循环外有明确类型的唯一返回值
    amount = 0.0
    valid = False

    while not valid:
        try:
            value = float(input(prompt))
            # 范围检查放在 try/except 之外，用独立 if 判断
            if value <= 0:
                print("金额必须大于 0，请重新输入。")
                continue
            # 成功时更新结果并置标志位，让循环自然退出
            amount = value
            valid = True
        except ValueError:
            print("输入无效，请输入数字金额。")

    # 循环外统一 return，检查器认定返回类型恒为 float，不含 None
    return amount


# 系统默认账户：账号 123456，密码 123456，默认余额一千万
account = BankAccount("尊贵客户", "123456", "123456", 10000000)

# 登录环节：账号或密码错误可反复重试，不会崩溃
while True:

    print('\n===== 银行系统（请先登录）=====')
    acc_input = input('请输入账号：').strip()
    pwd_input = input('请输入密码：').strip()

    if account.verify(acc_input, pwd_input):
        print(f'登录成功，欢迎您，{account.owner}！')
        break
    print('账号或密码错误，请重新登录。')

# 菜单主循环：登录后可反复执行各类操作，直到选择退出
while True:

    print('\n请选择要执行的操作：')
    print('1. 存款')
    print('2. 取款')
    print('3. 查询余额')
    print('0. 退出登录')

    choice = input('请输入您的选择（0 / 1 / 2 / 3）：').strip()

    if choice == '1':
        amount = get_amount('请输入存款金额：')
        account.deposit(amount)
        print(f'成功存入 {amount} 元，当前余额：{account.get_balance()} 元')
    elif choice == '2':
        amount = get_amount('请输入取款金额：')
        try:
            account.withdraw(amount)
            print(f'成功取出 {amount} 元，当前余额：{account.get_balance()} 元')
        except ValueError as e:
            print(f'取款失败：{e}')
    elif choice == '3':
        print(f'您的当前余额为：{account.get_balance()} 元')
    elif choice == '0':
        print('已退出登录，感谢使用，再见！')
        break
    else:
        print('无效的选项，请输入 0、1、2 或 3。')