#定义一个简单的在线购物车类，支持添加商品、删除商品、查看购物车内容以及计算总价的功能

#定义在线购物车类

class ShoppingCarts:

    """用于模拟简单的在线购物车，支持添加商品、删除商品、查看购物车内容以及计算总价的功能"""

    def __init__(self):

        """初始化购物车对象"""

        self.cart = {}  #初始化购物车为空字典，键为商品名称，值为包含数量和单价的字典

    def add_product(self):

        """
        添加商品到购物车
        :param product_name: 商品名称
        :param quantity: 商品数量
        :param price: 商品单价
        :return: None
        """

        product_name = input("请输入商品名称：")
        quantity = int(input("请输入商品数量："))
        price = float(input("请输入商品单价："))
        if product_name in self.cart:
            self.cart[product_name]['quantity'] += quantity
        else:
            self.cart[product_name] = {'quantity': quantity, 'price': price}
        print(f"已将{product_name}添加到购物车，数量为{quantity}，单价为{price}。")

    def remove_product(self):
        """
        从购物车删除商品
        :param product_name: 商品名称
        :return: None
        """
        product_name = input("请输入要删除的商品名称：")
        if product_name in self.cart:
            del self.cart[product_name]
            print(f"已将{product_name}从购物车删除。")
        else:
            print(f"{product_name}不在购物车中。")

    def view_cart(self):
        """
        查看购物车内容
        :return: None
        """
        print("购物车内容：")
        for product_name, product_info in self.cart.items():
            print(f"{product_name}：数量 {product_info['quantity']}，单价 {product_info['price']}，小计 {product_info['quantity'] * product_info['price']:.2f} 元")

    def calculate_total_price(self):
        """
        计算购物车总价
        :return: 购物车总价
        """
        total_price = sum([product_info['quantity'] * product_info['price'] for product_info in self.cart.values()])
        print(f"购物车总价为：{total_price:.2f} 元")
        return total_price
