#定义一个学生类，用于存储学生基本信息(如姓名、年龄、学号)，并提供查询这些信息的方法
from streamlit.type_util import async_generator_to_sync


#定义学生类

class Student:

    """存储学生基本信息"""

    #初始化学生对象

    def __init__(self,name,age,sid):

        self.name = name #学生姓名
        self.age = age   #学生年龄
        self.sid = sid   #学生学号

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

#示例使用，实例化对象

student = Student('张三',18,'1001')

print(student.get_name())
print(student.get_age())
print(student.get_sid())
