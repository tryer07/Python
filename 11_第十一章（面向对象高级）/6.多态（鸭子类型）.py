# ============================================================
# 多态演示（回顾上一节）：同一个方法名，不同子类对象执行各自的实现
# 多态 = "父类引用指向子类对象"，调用方法时以对象实际所属类的版本为准
# 典型应用：函数只面向父类编写（参数注解 car: Car），
#           传入任意子类对象都能正确触发各自重写的方法
#
# 鸭子类型（本节新增）：不看继承血统，只看有没有对应行为
# "如果它走起来像鸭子、游泳像鸭子，那它就是鸭子"
# Python 的类型注解只是静态提示，运行时不做强制校验
# ============================================================
from typing import Protocol

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

# ============================================================
# 鸭子类型演示：Duck / Dog / Pig 三个类之间没有任何继承关系，
# 只要各自都定义了 swimming 方法，就能被同一个函数当作"能游泳的对象"处理
# ============================================================

class Duck:
    def __init__(self, name):
        self.name = name

    # 输出带各自前缀，方便区分不同对象的调用形态
    def swimming(self):
        print(f"嘎嘎嘎，鸭子{self.name}在游泳")


class Dog:
    def __init__(self, name):
        self.name = name

    def swimming(self):
        print(f"汪汪汪，狗{self.name}在游泳")


class Pig:
    def __init__(self, name):
        self.name = name

    def swimming(self):
        print(f"哼哼哼，猪{self.name}在游泳")


# 带类型注解的版本：不再把参数注解成具体类 Duck，而是用 Protocol 按"行为"约束——
# 只要类里有 swimming 方法就自动满足 Swimmer，Duck/Dog/Pig 无需继承、无需声明，
# 检查器不会再报"应传入 Duck"，运行时调用仍按对象自己的 swimming 执行
class Swimmer(Protocol):
    def swimming(self) -> None: ...


def go_swimming(duck: Swimmer):
    duck.swimming()


print("\n---------- 测试1：带注解的 go_swimming 分别传入 Dog / Duck / Pig ----------")
# 注解只约束"会不会游泳"，不关心"是什么类"：传 Dog、Pig 既无编辑器告警，
# 运行也照常执行（类型注解本就不阻止运行，这条性质不变）
go_swimming(Dog("旺财"))
go_swimming(Duck("唐老鸭"))
go_swimming(Pig("猪八戒"))


# 对照：删掉类型注解后的版本，运行效果与带注解版完全一样（注解本就可选）
def go_swimming_no_annotation(duck):
    duck.swimming()


print("---------- 测试2：去掉注解后再次测试，输出不变 ----------")
go_swimming_no_annotation(Dog("旺财"))
go_swimming_no_annotation(Duck("唐老鸭"))
go_swimming_no_annotation(Pig("猪八戒"))

# 结论：Python 不要求参数"是什么类"，只要求"能做什么事"（有同名方法即可），
# 这就是鸭子类型；上一节的继承多态是"血统多态"，鸭子类型是"行为多态"；
# Protocol 正是官方推荐的给鸭子类型"标注行为"的写法，
# 既保留注解提示，又不会把"不是 Duck 就告警"的血统思维带回来
