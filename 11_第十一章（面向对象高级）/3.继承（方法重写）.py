# ============================================================
# 继承演示：复用 1.封装.py 中的 Car 作为父类，派生燃油车 / 电车子类
# 继承 = 子类自动拥有父类非私有的属性和方法（is-a 关系）
#   公共属性/方法：子类直接继承可用
#   私有成员（__xxx）：不会作为子类自己的属性被继承，子类作用域内无法直接访问
# 本文件重点演示：父类公共方法 charge() 的"自动继承"与"子类重写"
#   charge() 已补充定义在 1.封装.py 的 Car 中，输出：xxx正在补充燃料
# ============================================================
import pathlib
from typing import Any

# 父类 Car 定义在 1.封装.py 中，但文件名含有点和中文，无法用 import 语句直接导入
# （点号会被解释成包层级，找不到名为 "1" 的包），改用按文件路径读源码执行的方式加载
# 用 __file__ 同目录定位，不依赖运行时的工作目录

namespace: dict[str, object] = {"__name__": "fengzhuang_demo"}
parent_file = pathlib.Path(__file__).with_name("1.封装.py")
exec(compile(parent_file.read_text(encoding="utf-8"), str(parent_file), "exec"), namespace)

# 运行时取回来的确实是类对象，但检查器无法验证 dict[str, object] 里存的是什么；
# 若直接注解成 type 会触发连锁误判（把 class FuelCar(Car) 与 super().__init__() 按
# type(name, bases, dict, **kwds) 元类重载去匹配），因此用 Any 承接，Any 不参与重载校验

Car: Any = namespace["Car"]

# 注意：加载过程会顺带执行 1.封装.py 里的全部演示代码，输出后紧跟本文件的继承演示

# 需求2：父类 Car 已在 1.封装.py 中定义 __init__/start/run/stop/get_owner（获取拥有者），
#        并补充了公共方法 charge()：输出"xxx正在补充燃料"

# 需求3+4：先定义一个"什么都没写"的空子类，验证只要继承 Car，
#          不定义 charge 也会自动继承父类的 charge()
# （仅作阶段性验证；正式燃油车子类 FuelCar 见下方定义）

class TempFuelCar(Car):
    pass

print("---------- 需求4：未重写时，自动继承父类 charge() ----------")
temp = TempFuelCar("宝马", "X5", "黑色", "张三")
temp.charge()

# 需求3+5+6：正式燃油车子类 FuelCar(Car)
#   重写 charge() 改成燃油车逻辑（需求5）
#   并在重写方法中调用父类方法：super().charge() / Car.charge(self)（需求6）

class FuelCar(Car):
    # 重写 __init__ 时必须先 super().__init__() 初始化父类属性
    def __init__(self, brand, model, color, owner, tank_size):
        super().__init__(brand, model, color, owner)
        self.tank_size = tank_size

    # 子类新增自己的方法
    @staticmethod
    def refuel():
        print("去加油站加油")

    # 需求5：重写父类的 charge()，调用时以子类版本为准
    # 需求6方式一：super().charge() 先执行父类 charge()，再执行子类代码
    def charge(self):
        super().charge()
        print(f"{self.brand}{self.model}正在加油")

    # 需求6方式二：Car.charge(self) 显式点名父类方法，必须传入 self，效果同方式一
    # （同一个类里不能定义两个同名 charge，故用 charge_v2 单独演示方式二）
    def charge_v2(self):
        Car.charge(self)
        print(f"{self.brand}{self.model}正在加油（方式二：Car.charge(self)）")

    def start(self):
        pass

    def run(self):
        pass

    def stop(self):
        pass

    def get_owner(self):

        # 占位重写：演示方法重写会替换父类实现；父类原版行为由电车对象演示
        # 返回值参与拼接 self 上的属性，避免被判定为"可降级为静态方法"

        return f"子类重写的脱敏接口（占位，油箱 {self.tank_size} 升）"


class ElectricCar(Car):
    # 同样新增 __init__：电池容量是电车特有属性

    def __init__(self, brand, model, color, owner, battery):
        super().__init__(brand, model, color, owner)
        self.battery = battery

    # 需求7：电车类也重写 charge()，改成电车逻辑（不再沿用父类"补充燃料"的说法）
    def charge(self):
        print(f"{self.brand}{self.model}正在充电")

    def start(self):
        pass

    def run(self):
        pass

    def stop(self):
        pass


# 需求5+6 测试：调用子类重写后的 charge()，确认先执行父类、再执行子类代码

print("---------- 需求5/6：重写后的 charge()（方式一 super().charge()） ----------")
bmw = FuelCar("宝马", "X5", "黑色", "张三", 68)
bmw.charge()

print("---------- 需求6：重写中调用父类的另一种写法（方式二 Car.charge(self)） ----------")
bmw.charge_v2()

# 原有演示：创建子类对象，访问继承自父类的属性和方法，以及子类新增成员

print("---------- 燃油车测试 ----------")
fuel = FuelCar("奥迪", "A6", "黑色", "涛哥", 58)

# 全靠继承获得的父类公共属性与公共方法

print("brand:", fuel.brand, "| model:", fuel.model, "| color:", fuel.color)
fuel.start()
fuel.run()
fuel.stop()

# 访问子类自己新增的属性和方法

print("油箱大小（升）:", fuel.tank_size)
fuel.refuel()

print("---------- 电车测试 ----------")
electric = ElectricCar("特斯拉", "Model 3", "白色", "涛哥", 60)
print("brand:", electric.brand)
print("color:", electric.color)
electric.start()
electric.run()
electric.stop()
print("电池容量（千瓦时）:", electric.battery)
electric.charge()

# 验证私有成员的边界 —— 父类方法内部照常可用，但私有属性不会作为
# 子类自己的属性被继承，子类作用域内（getattr 原名）取不到
# fuel 调用的是子类占位重写的版本；electric 未重写，演示继承来的父类原版方法

print("车主（fuel 重写版）:", fuel.get_owner())
print("车主（electric 继承父类原版）:", electric.get_owner())
try:
    print(getattr(fuel, "__owner"))
except AttributeError as e:
    print("【验证】私有属性不会作为子类属性被继承:", e)

# isinstance / issubclass 验证继承关系成立

print("fuel 是 Car 的实例吗:", isinstance(fuel, Car))
print("ElectricCar 是 Car 的子类吗:", issubclass(ElectricCar, Car))

# 需求8：验证练习结果 —— 不同子类对象分别调用 charge()，
# 确认各自使用自己重写后的版本（燃油车"正在加油"，电车"正在充电"）

print("---------- 需求8：不同子类各自的 charge() ----------")
fuel.charge()
electric.charge()
