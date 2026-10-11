#定义一个父类Vehicle，包含一个方法describe，用于描述车辆具体信息。
#定义一个子类Car，继承自Vehicle，并重写describe方法，以提供关于汽车的特定信息。
#（优化版：两级选择——先选车辆类别，再选具体车辆查询，查完询问是否再次查询或退出）

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

#按类别组织可查询的车辆：键是类别名，值是该类别下的车辆对象列表
#目前子类只有 Car（汽车），因此只提供“汽车”这一类别

vehicle_types = {
    "汽车": [
        Car("丰田", "卡罗拉", 2024),
        Car("比亚迪", "汉", 2023),
        Car("特斯拉", "Model 3", 2025),
    ],
}

#辅助函数：读取一个范围内的整数编号（带输入校验，两级菜单复用）

def read_index(prompt, count):

    """
    反复提示用户输入，直到选择一个 1 ~ count 范围内的合法编号为止。
    :param prompt: 输入提示信息
    :param count: 可选择的数量上限
    :return: 对应的列表索引（int）
    """

    while True:
        try:
            choice = int(input(prompt))
        except ValueError:
            print("输入无效，请输入一个数字。")
            continue
        #范围校验独立于 try/except，避免合法数字绕过边界判断
        if 1 <= choice <= count:
            return choice - 1
        print(f"输入超出范围，请输入 1 ~ {count} 之间的数字。")

#辅助函数：展示某类别下的车辆列表

def show_vehicles(vehicles):

    """
    打印该类别下所有车辆的编号与基本信息。
    :param vehicles: 车辆对象列表
    """

    for i, vehicle in enumerate(vehicles, start=1):
        #子类汽车额外显示年份
        print(f"    {i}. {vehicle.make} {vehicle.model}（{vehicle.year} 年）")

#主程序

while True:

    #第一级：展示可查询的车辆类别，让用户先选择类别
    type_names = list(vehicle_types.keys())

    print("\n" + "=" * 40)
    print("欢迎使用车辆信息查询系统，请选择要查询的车辆类别：")
    print("=" * 40)

    for i, name in enumerate(type_names, start=1):
        count = len(vehicle_types[name])
        print(f"  {i}. {name}（可查询 {count} 辆）")

    print("-" * 40)

    type_index = read_index("请输入类别编号：", len(type_names))
    selected_type = type_names[type_index]
    vehicles = vehicle_types[selected_type]

    #第二级：进入所选类别，展示该类别下的车辆并选择一辆查询
    print(f"\n【{selected_type}】现有以下车辆可查询：")
    show_vehicles(vehicles)

    car_index = read_index("请输入要查询的车辆编号：", len(vehicles))
    selected = vehicles[car_index]

    #多态调用：子类对象执行重写后的 describe
    print("查询结果：", selected.describe())

    #查询完成后询问用户是再次查询还是退出程序
    again = input("是否再次查询信息？（y=继续 / 其他=退出）：").strip().lower()
    if again != "y":
        print("感谢使用，查询系统已退出。")
        break
