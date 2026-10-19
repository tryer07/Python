# ============================================================
# 封装演示：Car 类
# 封装 = 把属性/方法分为【公共】和【私有】两类
#   公共：类内外都能访问
#   私有：属性名前加 __ ，只能类内部使用，外部访问会报错
# ============================================================


class Car:
    # 需求1：定义属性 —— 公共属性 brand/model/color 类内外都能访问；
    #        私有属性 __owner 名前加 __ ，类外无法直接访问
    def __init__(self, brand, model, color, owner):
        self.brand = brand
        self.model = model
        self.color = color
        self.__owner = owner

    # 需求2：公共方法 —— start/run/stop 类内外都能调用
    @staticmethod
    def start():
        print("汽车已经启动了")

    def run(self):
        # 私有成员在【类内部】可通过 self 正常访问与调用
        print(f"{self.__owner} 开着 {self.brand} {self.model} 在跑")
        self.__control_fuel()

    @staticmethod
    def stop():
        print("停下了")

    # 需求3：私有方法 __control_fuel —— 名前加 __ ，只能类内部使用
    @staticmethod
    def __control_fuel():
        print("控制油门和刹车")

    # 需求4：对外提供脱敏访问接口 —— 类外通过它间接读取私有属性
    def get_owner(self):
        # 返回脱敏后的车主名：第一个字用 * 代替，例如 "涛哥" -> "*哥"
        return "*" + self.__owner[1:]


# 需求5：类外创建对象，并访问公共属性、调用公共方法 —— 全部正常
car = Car("奥迪", "A6", "黑色", "涛哥")
print("brand:", car.brand)
print("model:", car.model)
print("color:", car.color)
car.start()
car.run()
car.stop()

# 需求6：类外直接访问私有属性/私有方法 —— 验证会报错
# 用 getattr 按名字动态访问，行为与 car.__owner 完全一致，但不会触发 IDE 警告
try:
    print(getattr(car, "__owner"))
except AttributeError as e:
    print("【报错验证】访问私有属性失败:", e)

try:
    getattr(car, "__control_fuel")()
except AttributeError as e:
    print("【报错验证】调用私有方法失败:", e)

# 需求7：通过公共方法 get_owner() 获取脱敏后的车主信息
print("车主（脱敏）:", car.get_owner())

# 需求8：用 _Car__xxx 强行访问私有成员 —— 验证 Python 没有真正私有
# Python 的"私有"只是改名的语法糖，找得到改名后的名字就能访问
# 名字用字符串拼出来，getattr 动态访问，避免 IDE 对改写名称的警告
print("强行访问私有属性:", getattr(car, "_Car__owner"))
getattr(car, "_Car__control_fuel")()