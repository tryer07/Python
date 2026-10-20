# 应为类型 'Duck'，但实际为 'Dog'｜Python 面向对象高级（4）：多态与鸭子类型

> 系列说明：第十一章「面向对象高级」学习笔记第 4 篇。前三篇把封装、继承、多继承走完了，这一篇讲多态，以及它的野生版本——鸭子类型。

## 上半场：面向父类编程

前面我花了两篇讲子类重写 `charge()`：燃油车输出「正在加油」，电车输出「正在充电」，父类兜底输出「正在补充燃料」。

重写完了，然后呢？真正的收益要等到写**函数**的时候才显现。

我写了一个只做一件事的函数：

```python
def handler_charge(car: Car):
    car.charge()
```

它的参数注解是父类 `Car`，函数体里也只调用父类声明过的行为。测试代码：

```python
print("---------- 第一次测试：传入油车对象 ----------")
handler_charge(FuelCar("宝马", "X5", "黑色", "张三", 68))

print("---------- 第二次测试：传入电车对象 ----------")
handler_charge(ElectricCar("比亚迪", "汉", "白色", "李四", 60))

print("---------- 验证多态效果 ----------")
bmw = FuelCar("宝马", "X5", "黑色", "张三", 68)
han = ElectricCar("比亚迪", "汉", "白色", "李四", 60)
handler_charge(bmw)
handler_charge(han)
handler_charge(Car("大众", "迈腾", "银色", "王五"))
```

运行结果：

```
---------- 第一次测试：传入油车对象 ----------
宝马X5正在加油
---------- 第二次测试：传入电车对象 ----------
比亚迪汉正在充电
---------- 验证多态效果 ----------
宝马X5正在加油
比亚迪汉正在充电
大众迈腾正在补充燃料
```

**同一个函数，一句 `car.charge()`，传进去的对象不同，执行的就是不同的实现，连函数本身都不用改一行。** 传父类对象时它老老实实在跑父类原版。

这就是多态的实际用处。我之前的理解一直停在"子类可以重写父类方法"这句话上，写到这里才反应过来：重写只是**提供了可能性**，多态的价值在于**调用方可以完全不知道有几种车**。以后我再加一个 `HybridCar`（混动车），只要它继承 `Car` 并重写 `charge()`，`handler_charge` 一个字都不动就能正确工作。

我在第 5 篇的实战项目里真切用到了这条性质：系统里只有 `member.get_max_borrow()` 这一个调用点，普通会员返回 3、VIP 返回 6 + 等级，`LibrarySystem` 内部完全不需要 `if type(member) == VIPMember` 这种判断。

## 下半场：鸭子类型，以及一次翻车

接下来老师让做的例子让我觉得有点违背常识：定义三个**互相之间没有任何继承关系**的类。

```python
class Duck:
    def __init__(self, name):
        self.name = name

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
```

然后写一个函数，参数**明确注解成 `Duck`**：

```python
def go_swimming(duck: Duck):
    duck.swimming()


go_swimming(Dog("旺财"))    # 传的是狗
go_swimming(Duck("唐老鸭"))
go_swimming(Pig("猪八戒"))  # 传的是猪
```

我的第一反应是：`Dog` 跟 `Duck` 半毛钱继承关系都没有，这传进去不报错吗？

**运行完全不报错**，输出：

```
---------- 测试1：带注解的 go_swimming 分别传入 Dog / Duck / Pig ----------
汪汪汪，狗旺财在游泳
嘎嘎嘎，鸭子唐老鸭在游泳
哼哼哼，猪猪八戒在游泳
```

但是！**PyCharm 在第 104 行和第 106 行给了两条红线**：

```
应为类型 'Duck'，但实际为 'Dog'
应为类型 'Duck'，但实际为 'Pig'
```

我于是又写了一个**把注解完全删掉**的版本做对照：

```python
def go_swimming_no_annotation(duck):
    duck.swimming()


go_swimming_no_annotation(Dog("旺财"))
go_swimming_no_annotation(Duck("唐老鸭"))
go_swimming_no_annotation(Pig("猪八戒"))
```

输出逐行一致：

```
---------- 测试2：去掉注解后再次测试，输出不变 ----------
汪汪汪，狗旺财在游泳
嘎嘎嘎，鸭子唐老鸭在游泳
哼哼哼，猪猪八戒在游泳
```

## 这两件事同时成立，才是重点

「有红线」和「能跑」不矛盾，因为它们是**两个不同阶段**的事：

- 类型注解由 **编辑器/静态检查器**在写代码时读，它不认识运行时的对象，只做静态推断：`Dog` 不是 `Duck` 的子类，兼容性不成立，报警告。
- 函数调用由 **Python 解释器**在运行时执行，它只关心一件事：`duck` 这个对象身上有没有 `swimming` 这个方法。有就调，没有就 `AttributeError`。

所以那句名言在这个例子里落地了：**如果它走起来像鸭子、游泳起来像鸭子，那它就是鸭子。** Python 不在意"你是什么类"，只在意"你能做什么事"。

对比一下就很有意思：

- 上一节的 `handler_charge(car: Car)` 是**血统多态**——认的是继承关系，你必须真的是 `Car` 的后代。
- 这一节的 `go_swimming` 是**行为多态**——认的是方法名，你只要会 `swimming()` 就行，祖上是谁无所谓。

## 那两条红线该不该消

我的态度是：**要消，但不能用 `# type: ignore` 糊。**

糊注释是最省事的做法，但它等于对检查器说"闭嘴"。将来我真的传错东西（比如传了个只有 `fly()` 没有 `swimming()` 的对象），它会一起被闭嘴掉，我就再也得不到任何提醒了。

正确的方向是回到根因：告警的产生是因为我把参数注解成了**一个具体类** `Duck`。而鸭子类型讲的根本就不是类，是行为。所以我应该把注解也改成描述行为——用 `typing.Protocol`：

```python
from typing import Protocol


class Swimmer(Protocol):
    def swimming(self) -> None: ...


def go_swimming(duck: Swimmer):
    duck.swimming()
```

`Swimmer` 只声明一条规矩：**有 `swimming()` 这个签名的，就算数**。

改完之后：

- `Duck / Dog / Pig` 三个类**不需要继承 `Swimmer`，不需要任何 `register`，甚至不需要知道自己被注解了**，只要各自有 `swimming` 方法，就自动结构兼容。
- 两条「应为类型 'Duck'」告警从根源上消失了，因为注解不再关心血统。
- 运行时行为一行都没变。

我装了 mypy 做独立验证（不只看 IDE 面板）：

```
Success: no issues found in 1 source file
```

为什么要多跑这一步？因为我后来发现 **PyCharm 编辑器里的类型告警，不一定出现在 IDE 的问题列表回传结果里**——只看问题面板会误判成"零告警"。用命令行类型检查器交叉验证才靠得住。

顺带一说，`Protocol` 恰恰就是官方推荐的"给鸭子类型做标注"的写法。也就是说，我一开始用 `duck: Duck` 才是走偏了：既想要注解的好处，又用注解破坏了鸭子类型的精神。写 `Protocol` 反而两头都占——检查器有话可讲，运行时依旧自由。

## 小结

1. 多态的收益体现在**调用方**：函数面向父类写，新增子类不用改函数。
2. 鸭子类型不看继承，只看有没有对应方法；Duck / Dog / Pig 毫无关系也能被同一个函数处理。
3. 类型注解是**静态提示**，运行时不做强制校验，所以「编辑器报警告」和「程序能跑」完全不冲突。
4. 消类型告警要从根因改写法，不要用 `# type: ignore`；把"具体类注解"改成 `Protocol` 行为协议，是鸭子类型的正统标注方式。
5. 验证告警是否真清零，除了看 IDE 面板，还要跑一次独立的 mypy。

## 下一篇预告

第 5 篇（也是最后一篇）是**综合实战**：《书海灯塔 · 命令行图书借阅系统》。一个 command line 程序，会员登录、借书、还书、查看借阅、JSON 持久化，把这一章四件事全用进去——`Member` 把卡号密码私有化，`NormalMember / VIPMember` 继承它，`get_max_borrow()` 用多态区分借阅上限。

顺便我会交代一个类型告警连环坑：`Book.__init__` 里一句没有注解的 `self.available = min(available, total)`，怎么让三行八竿子打不着的代码同时冒出「应为类型 'int'，但实际为 'SupportsDunderLT[Any] | SupportsDunderGT[Any]'」。

---

**版权声明**：本文为个人学习笔记，代码均为教学演示用途，欢迎讨论指正，转载请注明出处，禁止商业使用（CC BY-NC-ND）。
