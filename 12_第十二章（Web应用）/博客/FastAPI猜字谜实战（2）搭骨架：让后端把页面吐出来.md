# FastAPI猜字谜实战（2）搭骨架：让后端把页面吐出来

> 这是系列的第二篇。上一篇我只会让后端吐一堆 JSON 数据，这一篇我要给它搭个真正的骨架：访问首页时能返回一个 HTML 页面，还能加载配套的 CSS 和 JS。这一步做完，后厨才算有了面向客人的那个窗口。

## 一、光吐 JSON 不够，我想让它返回页面

上一篇访问 `/` 返回的是 `{"message": "Hello World"}`，是数据不是页面。可我要做的是个能在浏览器里点的游戏，总得有个 html 界面被端出来才行。

所以我需要的不是 `return` 一个字典，而是 `return` 一个文件。fastapi 里干这事的是 `FileResponse`，你把一个文件路径给它，它就把这个文件作为响应吐给浏览器。

```
from starlette.responses import FileResponse

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
```

## 二、页面有了，可它的 CSS 和 JS 谁来管

一个前端页面通常会拆开写：`index.html` 是骨架，`css/style.css` 管样式，`js/game.js` 管交互。html 里我是这么引用它们的：

```
<link rel="stylesheet" href="/static/css/style.css">
<script src="/static/js/game.js"></script>
```

注意那个 `/static/...`。浏览器看到 html 里这些引用，会再发请求去要 `/static/css/style.css` 这些地址。问题是后端默认不认识这些地址，你得告诉它：凡是 `/static` 开头的请求，都去磁盘上的 `static` 目录里翻文件。

这活是 `StaticFiles` 干的，一行挂载搞定：

```
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
```

挂上之后，访问 `/static/css/style.css` 就会自动去 `static/css/style.css` 拿文件，我不用给每个静态文件单独写接口。

## 三、我不再写相对路径，改用锚点

这一步是我后来才想明白的。资源路径不能写成 `"static/index.html"` 这种纯相对路径，因为 Python 解析相对路径时看的是当前工作目录。而我用 PyCharm 运行时，工作目录可能是整个项目根，不一定是 `main.py` 所在的目录，一不对就找不到文件。

稳妥的办法是拿 `main.py` 自己所在的位置当锚点：

```
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SESSIONS_DIR = BASE_DIR / "sessions"
```

`Path(__file__).resolve().parent` 就是我这个文件所在目录的绝对路径。后面所有资源都从这个锚点往下拼，不管我从哪个目录启动程序，它都指得对。

## 四、把首页接口正式写出来

上面三块凑齐，我这个后端的最外层骨架就立起来了。先建 FastAPI 实例，再挂一个返回页面的首页接口：

```
app = FastAPI(title="汉字弥合")

@app.get("/", summary="打开首页", tags=["页面"])
def index():
    return FileResponse(STATIC_DIR / "index.html")
```

我在 `summary` 和 `tags` 填的是中文，这样上一篇提到的 `/docs` 页面里，这个接口就会显示成中文的打开首页、归到页面这一组，看着清爽。

## 五、跑起来验证骨架通了

服务启动后，我先访问 `http://localhost:8000/`，浏览器返回的是 html 页面而不是 JSON，说明 `FileResponse` 生效了。再访问 `http://localhost:8000/static/css/style.css`，样式文件能正常拿到，说明 `StaticFiles` 挂载也通了。

这一步我特意记住：后端搭骨架的关键就是两件事，把页面文件吐出去、把静态目录挂起来。至于 `static` 目录里的 html 里到底长什么样，那是前端的事，我先挖个坑放着。

## 六、骨架有了，接下来要往里塞数据

现在这个后端能返回页面了，但页面里还是空的，一局猜字谜的数据还没地方存。下一篇我就开始给它加真正的内容：做一个新建会话的接口，让玩家每开一局都能在磁盘上留下一份记录。
