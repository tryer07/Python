# 定义一个简单的在线购物车类，支持添加商品、删除商品、查看购物车内容以及计算总价的功能
# 实现的点：
# 1. 修复原版 8 个警告：add_product / remove_product 的 docstring 声明了形参，函数签名里却没有——
#    改为真正的形参传入，输入环节上移到主程序菜单，让"类只负责逻辑，菜单只负责交互"职责分离
# 2. 购物车字典补充显式类型注解，避免取出的商品信息被推断为 Any 而衍生新的类型警告
# 3. 数量/单价输入统一校验（标志位循环 + 循环外统一返回），输错不会崩溃，而是重新提示
# 4. calculate_total_price 只负责返回总价，打印交由调用方，不再"又打印又返回"
# 5. 类名由 ShoppingCarts 修正为单数形式的 ShoppingCart（文件内自包含，重命名安全）


# ---------- 在线购物车类 ----------
class ShoppingCart:

    """用于模拟一个简单的在线购物车，支持添加商品、删除商品、查看购物车内容以及计算总价"""

    def __init__(self):

        """初始化购物车对象"""

        # 键为商品名称，值为包含 'quantity' 与 'price' 的字典（显式注解，消除取值被推断为 Any 的问题）
        self.cart: dict[str, dict[str, float]] = {}

    def add_product(self, product_name, quantity, price):

        """
        添加商品到购物车
        :param product_name: 商品名称
        :param quantity: 商品数量（正整数）
        :param price: 商品单价（非负数）
        :return: 添加完成固定返回 True
        """

        if product_name in self.cart:
            # 商品已存在：数量累加，单价更新为本次输入
            self.cart[product_name]['quantity'] += quantity
            self.cart[product_name]['price'] = price
            total_count = self.cart[product_name]['quantity']
            print(f'  商品 {product_name} 已存在：累加 {quantity} 件，现有 {total_count} 件，单价更新为 {price} 元。')
        else:
            self.cart[product_name] = {'quantity': quantity, 'price': price}
            print(f'  已将 {product_name} 添加到购物车：数量 {quantity}，单价 {price} 元。')
        return True

    def remove_product(self, product_name):

        """
        从购物车删除商品
        :param product_name: 商品名称
        :return: 删除成功返回 True，商品不存在返回 False
        """

        if product_name in self.cart:
            del self.cart[product_name]
            print(f'  已将 {product_name} 从购物车删除。')
            return True
        print(f'  {product_name} 不在购物车中。')
        return False

    def view_cart(self):

        """查看购物车内容，购物车为空时给出提示"""

        if not self.cart:
            print('  当前购物车是空的。')
            return

        print('  购物车内容：')
        for product_name, product_info in self.cart.items():
            quantity = product_info['quantity']
            price = product_info['price']
            print(f'  {product_name}：数量 {quantity}，单价 {price} 元，小计 {quantity * price:.2f} 元')

    def calculate_total_price(self):

        """
        计算购物车总价
        :return: 购物车总价（浮点数；购物车为空时为 0.0）
        """

        # 初始值定为 0.0，保证任何分支下返回类型恒为 float，不含 None
        total_price = 0.0
        for product_info in self.cart.values():
            total_price += product_info['quantity'] * product_info['price']
        return total_price


# ---------- 输入辅助函数 ----------
def input_name(prompt):
    """
    输入商品名称：不能为空（标志位循环 + 循环外统一返回）
    :param prompt: 提示文字
    :return: 去除首尾空格后的名称
    """
    # 初始化结果变量与标志位，保证循环外有明确类型的唯一返回值
    name = ''
    valid = False

    while not valid:
        raw = input(prompt).strip()
        if not raw:
            print('  [输入无效] 商品名称不能为空，请重新输入。')
            continue
        # 成功时更新结果并置标志位，让循环自然退出
        name = raw
        valid = True

    return name


def input_quantity(prompt):
    """
    输入商品数量：必须是大于 0 的整数（标志位循环 + 循环外统一返回）
    :param prompt: 提示文字
    :return: 合法数量（整数）
    """
    quantity = 1
    valid = False

    while not valid:
        try:
            value = int(input(prompt))
        except ValueError:
            print('  [输入无效] 数量必须是整数，请不要输入小数、字母或符号。')
            continue

        # 范围校验放在 try/except 之外，用独立 if 判断
        if value <= 0:
            print('  [输入无效] 数量必须是大于 0 的正整数，请重新输入。')
            continue

        quantity = value
        valid = True

    return quantity


def input_price(prompt):
    """
    输入商品单价：必须是大于 0 的数字（标志位循环 + 循环外统一返回）
    :param prompt: 提示文字
    :return: 合法单价（浮点数）
    """
    price = 0.0
    valid = False

    while not valid:
        try:
            value = float(input(prompt))
        except ValueError:
            print('  [输入无效] 单价必须是数字，请不要输入字母或符号。')
            continue

        if value <= 0:
            print('  [输入无效] 单价必须大于 0，请重新输入。')
            continue

        price = value
        valid = True

    return price


# ---------- 主程序 ----------
if __name__ == '__main__':

    print('==== 欢迎使用简单在线购物车系统 ====')

    cart = ShoppingCart()

    # 菜单主循环：用户可反复选择操作，直到选择退出
    while True:

        print('\n请选择要执行的操作：')
        print('1. 添加商品')
        print('2. 删除商品')
        print('3. 查看购物车')
        print('4. 计算总价')
        print('0. 退出系统')

        choice = input('请输入您的选择（0 / 1 / 2 / 3 / 4）：').strip()

        if choice == '1':
            name = input_name('  请输入商品名称：')
            quantity = input_quantity('  请输入商品数量(正整数)：')
            price = input_price('  请输入商品单价(大于 0 的数字)：')
            cart.add_product(name, quantity, price)
        elif choice == '2':
            name = input_name('  请输入要删除的商品名称：')
            cart.remove_product(name)
        elif choice == '3':
            cart.view_cart()
        elif choice == '4':
            # 打印交由主程序完成，calculate_total_price 返回的恒为 float，格式化无 None 混入
            total = cart.calculate_total_price()
            print(f'  购物车总价为：{total:.2f} 元')
        elif choice == '0':
            print('已退出系统，感谢使用，再见！')
            break
        else:
            print('  无效的选项，请输入 0、1、2、3 或 4。')
