#实例方法

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

#测试

c1 = Car('铂金灰','BMW','X7',800000)
print(c1.__dict__)

#调用对象中的方法

c1.running()

total = c1.total_cost(discount=0.9,rate=0.1)
print(f'提车的总费用为：',total)

