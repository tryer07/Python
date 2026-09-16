#魔法方法
class Car:
    def __init__(self,c_color,c_brand,c_name,c_price):
        #__init__是初始化的方法，会在对象创建时自动调用，可以在该方法中为对象设置新的属性
        #__self__是第一个参数，表示当前所创建出来的实例对象
        self.color = c_color
        self.brand = c_brand
        self.name = c_name
        self.price = c_price
        print('类的对象初始化完毕，对象属性已经添加完毕~')

    #定义实例方法

    def running(self):
         print(f'{self.brand} {self.name} 正在高速行驶中')

    def total_cost(self,discount = 1.0,rate = 0.1):
        """
        计算提车的总费用
        :param discount:折扣
        :param rate:税率
        :return:提车的总费用
        """
        total_cost = self.price * discount + self.price * rate
        return total_cost
    #魔法方法

    def __str__(self):
        return f'{self.color} {self.brand} {self.name} {self.price}'

    from typing import Any

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Car):
            return NotImplemented  # type: ignore
        return (self.color == other.color and
                self.brand == other.brand and
                self.name == other.name and
                self.price == other.price)

    def __lt__(self,other):
        return self.price < other.price


c1 = Car('铂金灰','BMW','X7',800000)
print(c1.__dict__)

print(c1)

c2 = Car('深空蓝','奔驰','E300',450000)
print(c2.__dict__)

print(c2)

print(c1 == c2)

print(c1 > c2) #这里写大于号也是没问题的，less than逻辑取反就是了。
