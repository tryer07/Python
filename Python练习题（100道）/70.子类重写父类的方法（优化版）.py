#定义一个父类Vehicle，包含一个方法describe，用于描述车辆具体信息。
#定义一个子类Car，继承自Vehicle，并重写describe方法，以提供关于汽车的特定信息。
#（优化版：用户可在运行界面自行选择要查询的车辆信息）

#定义父类

class Vehicle:
    """
    定义一个父类Vehicle，包含一个方法describe，用于描述车辆具体信息。
    """

    #初始化车辆对象

    def __init__(self, make, model):

        self.make = make
        self.model = model

    #描述车辆信息

    def describe(self):

        return f"这辆车的制造商是 {self.make}，型号是 {self.model}。"

#定义子类，继承自父类

class Car(Vehicle):
    """
    定义一个子类Car，继承自Vehicle，并重写describe方法，以提供关于汽车的特定信息。
    """

    def __init__(self, make, model, year):

        #调用父类的__init__，初始化制造商与型号
        super().__init__(make, model)

        #再初始化子类特有的属性
        self.year = year

    #重写父类方法

    def describe(self):

        """
        重写父类方法，提供关于汽车的特定信息。
        :return: str
        """

        return f"这是一辆 {self.year} 年产的 {self.make} {self.model}。"

#构建一个车辆车库，里面既有普通车辆（父类对象），也有汽车（子类对象）

garage = [
    Vehicle("大众", "高尔夫"),
    Car("丰田", "卡罗拉", 2024),
    Vehicle("本田", "思域"),
    Car("比亚迪", "汉", 2023),
    Car("特斯拉", "Model 3", 2025),
]

#辅助函数：读取一个车辆编号（带输入校验）

def read_vehicle_index(garage):

    """
    反复提示用户输入，直到选择一个合法的车辆编号为止。
    :param garage: 车辆列表
    :return: 车辆在列表中的索引（int）
    """

    while True:
        try:
            choice = int(input(f"请输入要查询的车辆编号（1 ~ {len(garage)}）："))
            if 1 <= choice <= len(garage):
                return choice - 1
            print(f"输入超出范围，请输入 1 ~ {len(garage)} 之间的数字。")
        except ValueError:
            print("输入无效，请输入一个数字。")

#辅助函数：展示车库菜单，让用户清楚看到可以查询哪些车辆

def show_menu(garage):

    """
    打印车库中所有车辆的编号与基本信息，方便用户选择要查询的车辆。
    :param garage: 车辆列表
    """

    print("\n" + "=" * 40)
    print("欢迎使用车辆信息查询系统，车库中现有以下车辆：")
    print("=" * 40)

    for i, vehicle in enumerate(garage, start=1):
        #子类汽车额外显示年份，父类车辆只显示品牌与型号
        if isinstance(vehicle, Car):
            info = f"{vehicle.make} {vehicle.model}（{vehicle.year} 年）"
        else:
            info = f"{vehicle.make} {vehicle.model}"
        #用一个简短标签说明每辆车的类别
        kind = "汽车" if isinstance(vehicle, Car) else "普通车辆"
        print(f"  {i}. [{kind}] {info}")

    print("-" * 40)

#主程序

while True:

    #每一轮查询前都重新展示菜单，让用户随时看到可查询的车辆
    show_menu(garage)

    index = read_vehicle_index(garage)

    #从列表中取出用户选中的对象，多态调用其 describe 方法
    selected = garage[index]

    #父类对象执行父类describe，子类对象执行重写后的describe
    print("查询结果：", selected.describe())

    #询问用户是否继续查询其他车辆
    again = input("是否继续查询其他车辆？（y/n）：").strip().lower()
    if again != "y":
        print("感谢使用，查询系统已退出。")
        break
