#实例属性与类属性

class Car:
    #类属性(所有实例对象共享)

    wheel = 4 #轮胎数量
    tax_rate = 0.1 #购置税税率

    def __init__(self,c_color,c_brand,c_name,c_price):
        #__init__是初始化的方法，会在对象创建时自动调用，可以在该方法中为对象设置新的属性
        #__self__是第一个参数，表示当前所创建出来的实例对象

        #实例属性(各个对象特有的数据)

        self.color = c_color
        self.brand = c_brand
        self.name = c_name
        self.price = c_price
        #self.wheel = 2 #这里不同于全局变量和局部变量之间的优先级，通过实例对象查找属性时，会先查找实例属性，若实例属性不存在，才会查找类属性。
        print('类的对象初始化完毕，对象属性已经添加完毕~')


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


c1 = Car('铂金灰','BMW','X7',800000)
print(c1.__dict__)
print(c1.brand)
print(c1.wheel) #通过实例对象查找属性时，会先查找实例属性，若实例属性不存在，才会查找类属性。
