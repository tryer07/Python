# ============================================================
# 多态演示：同一个方法名，不同子类对象执行各自的实现
# 多态 = "父类引用指向子类对象"，调用方法时以对象实际所属类的版本为准
# 典型应用：函数只面向父类编写（参数注解 car: Car），
#           传入任意子类对象都能正确触发各自重写的方法
# ============================================================

# 父类 Car：公共属性 + 公共方法 charge（子类未重写时的兜底行为）
class Car:
    def __init__(self, brand, model, color, owner):
        self.brand = brand
        self.model = model
        self.color = color
        self.owner = owner

    def charge(self):
        print(f"{self.brand}{self.model}正在补充燃料")


# 子类 FuelCar（油车）：重写 charge 改成燃油车逻辑
class FuelCar(Car):
    def __init__(self, brand, model, color, owner, tank_size):
        super().__init__(brand, model, color, owner)
        self.tank_size = tank_size

    def charge(self):
        print(f"{self.brand}{self.model}正在加油")


# 子类 ElectricCar（电车）：重写 charge 改成电车逻辑
class ElectricCar(Car):
    def __init__(self, brand, model, color, owner, battery):
        super().__init__(brand, model, color, owner)
        self.battery = battery

    def charge(self):
        print(f"{self.brand}{self.model}正在充电")


# 需求：定义处理补充燃料的函数
# 参数注解 car: Car 表示"面向父类编程"——实际可以传入 Car 或它的任意子类对象，
# car.charge() 执行哪个版本，由传入对象的实际类型决定（这就是多态）
def handler_charge(car: Car):
    car.charge()


print("---------- 第一次测试：传入油车对象 ----------")
handler_charge(FuelCar("宝马", "X5", "黑色", "张三", 68))

print("---------- 第二次测试：传入电车对象 ----------")
handler_charge(ElectricCar("比亚迪", "汉", "白色", "李四", 60))

print("---------- 验证多态效果 ----------")
# 同一个 handler_charge，传入不同子类对象，执行各自重写的 charge；
# 传父类对象时则执行父类原版 charge，互不干扰
bmw = FuelCar("宝马", "X5", "黑色", "张三", 68)
han = ElectricCar("比亚迪", "汉", "白色", "李四", 60)
handler_charge(bmw)
handler_charge(han)
handler_charge(Car("大众", "迈腾", "银色", "王五"))
