#定义一个父类Vehicle，包含一个方法describe，用于描述车辆具体信息。
#定义一个子类Car，继承自vehicle，并重写describe方法，以提供关于汽车的特定信息

#定义父类

class Vehicle:
    """
    定义一个父类Vehicle，包含一个方法describe，用于描述车辆具体信息。
    """

    #初始化车辆对象

    def __init__(self,make,model):

        self.make = make
        self.model = model

    #描述车辆信息

    def describe(self):

        return f"这辆车的制造商是 {self.make}，型号是 {self.model}。"

#定义子类，继承自父类

class Car(Vehicle):
    """
    定义一个子类Car，继承自vehicle，并重写describe方法，以提供关于汽车的特定信息
    """

    def __init__(self, make, model, year):

        #调用父类的__init__，初始化制造商与型号
        super().__init__(make, model)

        #再初始化子类特有的属性
        self.year = year

    #重写父类方法

    def describe(self):

        """
        重写父类方法，提供关于汽车的特定信息
        return: str
        """

        return f"这辆车的年份是 {self.year}。"

#示例使用

car = Car("丰田", "卡罗拉", 2024)

#描述汽车基本信息

print(car.describe())

#调用父类的describe，展示制造商与型号信息

print(Vehicle.describe(car))


