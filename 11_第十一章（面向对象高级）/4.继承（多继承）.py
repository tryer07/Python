# ============================================================
# 多继承演示：问界汽车（WenjieCar）同时继承 Car 与 HuaweiAIDriven
# 多继承 = 子类一次性获得多个父类的成员，父类之间用逗号分隔
# 同名成员的查找顺序遵循 MRO：子类自身 -> 第一个父类 -> 第二个父类 -> ... -> object
# ============================================================

# 需求1+2：父类 Car，公共属性 + start/run/stop/get_owner/charge
class Car:
    def __init__(self, brand, model, color, owner):
        self.brand = brand
        self.model = model
        self.color = color
        self.owner = owner

    def start(self):
        print(f"{self.brand} {self.model} 启动")

    def run(self):
        print(f"{self.owner}驾驶着{self.brand}{self.model}正在行驶")

    def stop(self):
        print(f"{self.brand} {self.model} 停止")

    def get_owner(self):
        print(f"拥有者是：{self.owner}")

    def charge(self):
        print(f"{self.brand} {self.model} 正在充电")


# 需求3：父类 HuaweiAIDriven，version 属性（默认 V1.0）+ run
class HuaweiAIDriven:
    def __init__(self, version="V1.0"):
        self.version = version

    def run(self):
        print(f"使用华为AI智能驾驶系统 {self.version} 正在行驶")


# 需求4+5+10：先定义"空"多继承子类，观察默认行为 —— 默认的 __init__ 与同名 run
# 都取第一个父类 Car 的版本
class WenjieCar(Car, HuaweiAIDriven):
    pass

print("---------- 阶段1：空子类的默认行为 ----------")
wc = WenjieCar("BMW", "X5", "黑色", "张三")
print(wc)
# 实例属性只有 Car 的 4 个、没有 version => 证明调用的是第一个父类 Car.__init__
print("实例属性:", wc.__dict__)

# 需求7：MRO 方法解析顺序 = WenjieCar -> Car -> HuaweiAIDriven -> object
print("MRO:", WenjieCar.__mro__)

# 需求10：子类未重写 run()，默认执行第一个父类 Car.run()
wc.run()

# 顺带验证从 Car 继承来的其他公共方法
wc.start()
wc.get_owner()
wc.charge()
wc.stop()

# 需求6：交换父类顺序的影响（用临时类演示，相当于把 WenjieCar 的
# (Car, HuaweiAIDriven) 临时改成 (HuaweiAIDriven, Car)，验证完保持原顺序即可）
class WenjieCarSwapped(HuaweiAIDriven, Car):
    pass

print("\n---------- 阶段2：交换父类顺序 ----------")
print("交换后 MRO:", WenjieCarSwapped.__mro__)
# __init__ 变成排前面的 HuaweiAIDriven 的，只能传 version
ok = WenjieCarSwapped("V2.0")
print("按新顺序传参成功:", ok.__dict__)
ok.run()  # 同名 run 也改成优先调用排前面的 HuaweiAIDriven.run
try:
    WenjieCarSwapped("BMW")
except TypeError as e:
    print("【报错验证】仍按 Car 的 4 个参数传:", e)

# 需求8+9：子类重写 __init__，手动整合两个父类的属性
# super().__init__(...) 按 MRO 调用第一个父类 Car，等价写法为 Car.__init__(self, ...)
# 需求11：子类重写 run()，分别显式调用两个父类的 run()，让两边都执行
class WenjieCar(Car, HuaweiAIDriven):
    def __init__(self, brand, model, color, owner, version="V1.0"):
        super().__init__(brand, model, color, owner)
        HuaweiAIDriven.__init__(self, version)

    def run(self):
        Car.run(self)
        HuaweiAIDriven.run(self)

print("\n---------- 阶段3：子类重写 __init__ 与 run ----------")
wc1 = WenjieCar("BMW", "X5", "黑色", "张三")
print("不传 version（默认值）:", wc1.__dict__)
wc2 = WenjieCar("BMW", "X5", "黑色", "张三", "V1.1")
print("传 version（自定义值）:", wc2.__dict__)

# 重写后两个父类的 run() 都会执行
wc1.run()
wc2.run()
