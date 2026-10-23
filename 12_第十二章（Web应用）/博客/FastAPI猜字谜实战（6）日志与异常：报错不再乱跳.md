# FastAPI猜字谜实战（6）日志与异常：报错不再乱跳

> 这是系列的第六篇。前面几篇我一路 `print` 走过来，能跑是能把，但真出了错，浏览器那边一片空白，控制台一堆原始堆栈，看着头大。这一篇我把调试输出正规化，再给整个后端加个兜底。

## 一、print用多了，我自己都嫌乱

一开始我在每个接口里 `print` 几句，看看走到哪一步了。功能少还行，等接口多起来，我发现问题：这些 `print` 没有时间、没有级别、不知道是哪一行打的，出了事翻半天找不到源头。而且它们没法按需关闭，正式上线了一堆调试信息还在那刷屏。

所以我决定换成正规的 `logging`。

## 二、一行配置，日志立刻像样了

我在文件顶部配一次，之后全用 `logging.info`：

```
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)
```

这个 `format` 是我特意挑的，打出来一条日志带着时间、级别、文件名、行号、内容五样东西。之前那些 `print` 我全替换成了 `logging.info`，写法没变、就是把 `print` 换了个名，可输出质量完全是两个世界。

级别设成 `INFO`，是为了平时开发能看见普通信息。想安静的时候我可以临时把它调到 `ERROR`，那些 `info` 就不刷了，只留重要的。这就是 `print` 给不了我的开关。

## 三、顺手关掉访问日志的刷屏

配好 logging 我还发现一个吵的东西：uvicorn 每收到一个请求，就在控制台打一行 `GET /... 200 OK` 这种访问日志。开发时我压根不需要它，反而盖住了我自己的业务日志。

我在启动时加了个参数把它关了：

```
uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)
```

关掉之后，那些每条请求的访问行没了，控制台清爽很多，只剩 uvicorn 自己的启动信息和我的 `logging` 输出。

## 四、真正让我头疼的是报错

日志规整了，可还有个更大的问题。比如详情接口去读一个根本不存在的会话文件，`open` 直接抛异常。没处理的话会怎样？前端 fetch 收到的是一个残缺的、甚至空白的响应，页面上什么提示都没有，玩家一脸懵。而我控制台里蹦出来的是一整段原始 traceback，又长又难看。

我要的是：不管后端哪出错，都别把内部堆栈甩给前端，而是老老实实返回一个统一的错误 JSON，同时把真正的错误给我记到日志里。

## 五、一个全局异常处理器兜住所有

fastapi 给了我这个能力，就是异常处理器。我注册一个兜底的，捕获所有没被处理的异常：

```
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
def handler_exception(request: Request, exception: Exception) -> JSONResponse:
    logging.error(f"处理异常：请求路径 {request.url}，错误信息：{exception}")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误请联系管理员", "data": None},
    )
```

它的逻辑是：一旦哪个接口抛了我没接住的异常，就都汇到这来。我用 `logging.error` 把出事的网址和错误信息记下来，这部分只有我开发者看得到。然后我返回一个 `JSONResponse`，状态码 500，内容却还是我那个 `code / message / data` 三件套格式。

这样前端永远拿到的都是规范的 JSON，它能认出 `code` 不是 200、然后把 message 显示给玩家，页面不会崩、不会一片空白。

## 六、验证：故意读一个不存在的会话

我起了服务，专门去访问一个乱写的 id，比如 `/api/sessions/not-exist-123`，那个文件根本不存在，接口里的 `open` 必然抛异常。

结果符合预期：我这边控制台看到一条 `ERROR` 级日志，带着请求路径和具体错误；而前端收到的却是干净的 `{code: 500, message: 服务器内部错误..., data: null}`，不是半截 HTML 也不是空白。

有一点我提前说明，免得以后困惑：即使有了这个处理器，uvicorn 控制台还是会额外打一段原始堆栈，那是它自带的行为，我的处理器管不着，但它不影响前端拿到的那个干净 JSON。

后端到这儿算是又稳了一层：日志能定位，出错不甩锅给前端。可它现在还是只能靠 `/docs` 去点，玩家没法真正玩。下一篇我就给它配个真正的脸：前端聊天页面。
