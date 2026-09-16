#类的定义(不推荐动态地为对象添加属性)

#定义方式一：动态地为对象添加属性

# class Car:
#     pass

#创建对象

# c1 = Car()

#动态地为对象添加属性

# c1.color = 'red'
# c1.brand = 'BMW'
# c1.name = 'X5'
# c1.price = 500000
#
# print(c1.color)
# print(c1.brand)
# print(c1.name)
# print(c1.price)

# print(c1) #这里如果这样直接打印的话会将对象的内存地址以16进制的方式打印出来，并不是真正运行想要的结果。

#打印属性(将对象的属性以字典的形式输出出来)

# print(c1.__dict__)

#定义方法二：推荐的定义方式

class Car:
    def __init__(self,c_color,c_brand,c_name,c_price):
        #__init__是初始化的方法，会在对象创建时自动调用，可以在该方法中为对象设置新的属性
        #__self__是第一个参数，表示当前所创建出来的实例对象
        self.color = c_color
        self.brand = c_brand
        self.name = c_name
        self.price = c_price
        print('类的对象初始化完毕，对象属性已经添加完毕~')

#创建对象

c1 = Car('铂金灰','BMW','X7',800000)
print(c1.__dict__)

c2 = Car('深空蓝','奔驰','E300',450000)
print(c2.__dict__)