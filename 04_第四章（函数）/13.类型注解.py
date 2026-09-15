#类型注解

#变量定义

a: int = 100
score: float = 98.5
hobby: str = 'Python'
flag: bool = True
pic: None = None

name1: list[str | int] = ['A', 'B', 'C'] #list[str | int]此时这样写可以保证str和int类型都可以在这个list中使用

phone1: set[str] = {'18806092052','18020805089'}

options: dict[str,int] = {'count':2 , 'total':10}

goods: tuple[str,int,int] = ('手机',5090,1)

name1.append('D')

name1.append(3)

# name1.append(100.0)
#类型注解只是起到语法提示作用，并不会影响程序运行的结果，比如上面添加的数据类型是float类型，同样会在控制台输出出来，只不过会有警告信息。


