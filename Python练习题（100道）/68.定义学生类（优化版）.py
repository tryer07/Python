# 定义一个学生类，用于存储学生基本信息(如姓名、年龄、学号)，并提供查询这些信息的方法
# 优化版：支持用户自定义输入 + 输入校验 + 美化输出


# 定义学生类
class Student:

    """存储学生基本信息，并提供查询方法"""

    # 初始化学生对象
    def __init__(self, name, age, sid):
        self.name = name  # 学生姓名
        self.age = age    # 学生年龄
        self.sid = sid    # 学生学号

    def get_name(self):
        """
        获取学生姓名
        :return: 学生姓名
        """
        return self.name

    def get_age(self):
        """
        获取学生年龄
        :return: 学生年龄
        """
        return self.age

    def get_sid(self):
        """
        获取学生学号
        :return: 学生学号
        """
        return self.sid

    def info(self):
        """
        以美观的格式汇总输出学生信息
        :return: 格式化后的字符串
        """
        line = '-' * 30
        return (
            f'{line}\n'
            f'  学生信息卡\n'
            f'{line}\n'
            f'  姓    名：{self.name}\n'
            f'  年    龄：{self.age} 岁\n'
            f'  学    号：{self.sid}\n'
            f'{line}'
        )


# ---------- 输入辅助函数 ----------
def input_name():
    """输入姓名：不能为空"""
    while True:
        name = input('请输入学生姓名：').strip()
        if name:
            return name
        print('[输入无效] 姓名不能为空，请重新输入。')


def input_age():
    """输入年龄：必须是整数，且在 0 ~ 150 之间"""
    while True:
        raw = input('请输入学生年龄(0-150 的整数)：').strip()
        try:
            age = int(raw)
        except ValueError:
            print('[输入无效] 年龄必须是整数，请不要输入字母或符号。')
            continue

        # 范围校验必须放在 try/except 之外，否则正常数字会绕过这里
        # 边界用 or：小于 0 或 大于 150 都算越界
        if age < 0 or age > 150:
            print('[输入无效] 年龄超出合理范围(0-150)，请重新输入。')
            continue

        return age


def input_sid():
    """输入学号：不能为空"""
    while True:
        sid = input('请输入学生学号：').strip()
        if sid:
            return sid
        print('[输入无效] 学号不能为空，请重新输入。')


# ---------- 主程序 ----------
if __name__ == '__main__':
    print('==== 欢迎使用学生信息录入系统 ====')
    print('请按提示依次输入以下信息：\n')

    name = input_name()
    age = input_age()
    sid = input_sid()

    # 实例化学生对象
    student = Student(name, age, sid)

    # 使用查询方法
    print('\n【使用 get_xxx() 方法查询】')
    print(f'  姓名 -> {student.get_name()}')
    print(f'  年龄 -> {student.get_age()}')
    print(f'  学号 -> {student.get_sid()}')

    # 使用格式化输出
    print('\n【使用 info() 方法格式化输出】')
    print(student.info())