#案例

#目标：完成教务管理系统的开发，教务管理系统可以管理在校学生的成绩信息，通过控制台菜单与用户交互。

#要求
#1.采用面向对象编程思想完成如下需求
#2.添加学生成绩，根据输入的学生姓名、语文数学英语成绩，记录在系统中
#3.修改学生成绩，根据输入的学生姓名，修改对应学生成绩
#4.删除学生成绩，根据输入的学生姓名，删除对应学生成绩
#5.查询指定学生成绩，根据输入的学生姓名查找对应学生的成绩并输出
#6.展示全部学生成绩

# 案例：教务管理系统

# 学生类
class Student:
    def __init__(self, name, Chinese, Math, English):
        # 初始化学生对象，设置姓名和三科成绩
        self.name = name
        self.Chinese: float = Chinese   # 类型提示，建议传入数字
        self.Math: float = Math
        self.English: float = English

    # 格式化输出学生信息，包括总分
    def __str__(self):
        return (f'姓名：{self.name} | 语文：{self.Chinese} | 数学：{self.Math} | '
                f'英语：{self.English} | 总分：{self.Chinese + self.Math + self.English}')

    # 修改学生成绩，参数为 None 时表示不修改该科
    def update_score(self, Chinese=None, Math=None, English=None):
        if Chinese is not None:
            self.Chinese = Chinese
        if Math is not None:
            self.Math = Math
        if English is not None:
            self.English = English


# 教务管理系统类
class EduManagement:
    system_version = '1.0'
    system_name = '教务管理系统'

    def __init__(self):
        # 用列表存储所有学生对象
        self.student_list = []

    # 添加学生成绩
    def add_student(self):
        name = input('请输入学生姓名：')

        # 检查姓名是否已存在，防止重复添加
        for s in self.student_list:
            if s.name == name:
                print('该学生已经存在，添加失败~')
                return

        # 输入三科成绩
        Chinese = int(input('请输入学生语文成绩：'))
        Math = int(input('请输入学生数学成绩：'))
        English = int(input('请输入学生英语成绩：'))

        # 校验成绩范围
        if 0 <= Chinese <= 100 and 0 <= Math <= 100 and 0 <= English <= 100:
            stu = Student(name, Chinese, Math, English)
            self.student_list.append(stu)
            print('学生信息添加成功~')
        else:
            print('各科成绩必须在0-100之间！')

    # 修改学生成绩
    def update_student(self):
        name = input('请输入学生姓名：')

        # 根据姓名查找学生
        for s in self.student_list:
            if s.name == name:
                print(f'当前成绩：{s}')
                Chinese = int(input('请输入修改后的学生语文成绩：'))
                Math = int(input('请输入修改后的学生数学成绩：'))
                English = int(input('请输入修改后的学生英语成绩：'))

                # 校验成绩范围
                if 0 <= Chinese <= 100 and 0 <= Math <= 100 and 0 <= English <= 100:
                    s.update_score(Chinese, Math, English)
                    print('成绩修改成功~')
                    print(f'修改后的成绩：{s}')
                    return
                else:
                    print('各科成绩必须在0-100之间！')
                    return   # 成绩不合法则直接结束，不再执行后面的“未找到”提示

        print('未找到该学生，执行失败！')

    # 删除学生成绩
    def delete_student(self):
        name = input('请输入要删除的学生姓名：')

        # 查找并删除
        for s in self.student_list:
            if s.name == name:
                self.student_list.remove(s)
                print('学生信息删除成功！')
                return

        print('未找到该学生，删除失败！')

    # 查询指定学生成绩
    def query_student(self):
        name = input('请输入要查询的学生姓名：')

        for s in self.student_list:
            if s.name == name:
                print(f'学生信息：{s}')
                return

        print('未找到该学生！')

    # 展示全部学生成绩
    def list_student(self):
        if not self.student_list:
            print('暂无学生信息')
        else:
            for s in self.student_list:
                print(s)

    # 运行系统主菜单
    def run(self):
        print(f'欢迎使用教学管理系统 V{EduManagement.system_version}')

        while True:
            print()
            print('# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #')
            print('#   1.添加学生 2.修改学生 3.删除学生 4.查询指定学生 5.查询所有学生 6.退出系统    #')
            print('# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #')
            print()

            # 修正：这里必须用 input() 获取输入，否则 choice 永远是固定字符串，导致无限循环
            choice = input('请选择要执行的操作，输入1-6：')

            match choice:
                case '1':
                    self.add_student()
                case '2':
                    self.update_student()
                case '3':
                    self.delete_student()
                case '4':
                    self.query_student()
                case '5':
                    self.list_student()
                case '6':
                    print('Bye~')
                    break
                case _:
                    print('输入错误！请选择1-6之间的菜单功能！')


# 测试
if __name__ == '__main__':
    edu_management = EduManagement()
    edu_management.run()

