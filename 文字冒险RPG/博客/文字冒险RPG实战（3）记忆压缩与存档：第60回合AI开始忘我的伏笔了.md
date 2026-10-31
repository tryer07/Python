# 文字冒险RPG实战（3）记忆压缩与存档：第60回合，AI开始忘我的伏笔了

> 这是系列的第三篇。前两篇把数值管住了，这一篇处理另一个长线问题：游戏越玩越久，AI 主持人的记忆越来越不够用。顺便把这个项目的存档系统一块讲了，里面有几个我特意设防的小细节。

## 一、历史像雪球一样越滚越大

先看我每回合干了什么。玩家发一个行动，AI 回一段剧情，这两条都 append 进 `messages`，下次请求整包带过去：

```
session_data["messages"].append({"role": "user", "content": request.message})
session_data["messages"].append({"role": "assistant", "content": clean_story})
```

看起来没问题，但玩到三十回合，里面就是六十条记录，每条剧情一两百字。两个后果一起来：一是每次请求的 token 越滚越大，响应变慢、账单变厚；更要命的是第二个，AI 对长列表中段的注意力会明显变差，我二十回合前埋的一个据点伏笔，它转头就当我死了。

## 二、纯截断省事，但会断片

最容易的做法是写死一个上限，超了就掐头，比如永远只带最近四十条：

```
session_data["messages"] = session_data["messages"][-40:]
```

我拿这个版本测了几局，剧情立刻开始精神分裂：被救过的恩人忘了报恩，丢了的车又出现在车库里。原因很简单，GM 的人设要求它连贯，可它手里已经没有前文了，连贯无从谈起。

砍历史躲不掉，那就只能让被砍掉的部分换个形式活下来。

## 三、让 AI 自己写前情摘要

我的办法是：砍之前，先把要扔的老历史交给 AI，让它自己压缩成一段剧情摘要。这个活儿有专门的提示词，我把干活的称呼从 GM 换成记录员：

```
def build_summary_prompt(messages) -> list:
    history_text = "\n".join(
        f"{'玩家' if m['role'] == 'user' else 'GM'}：{m['content']}" for m in messages
    )
    return [
        {
            "role": "system",
            "content": "你是跑团记录员。把下面这段游戏经历压缩成 120 字以内的前情摘要，"
                       "只保留：玩家去过哪、遇到过谁、结下什么仇或恩、埋下但还没收回的线索、"
                       "失去或得到的要紧物品。不加评论，不写状态数值，直接给摘要正文。",
        },
        {"role": "user", "content": history_text},
    ]
```

这段提示词里我字字都在做减法：120 字封顶，不然摘要本身变成新的负担；点名只保留五类信息，把"氛围描写"这种没用的水分挤掉；特意写了不写状态数值，因为数值账在角色卡里另有一份，摘要掺数字反而容易和现状打架。

## 四、触发时机和降级路线

压缩不是每回合都做，我设了个阈值：满六十条才动手一次。

```
if len(session_data["messages"]) > 60:
    old_messages = session_data["messages"][:-40]
    try:
        summary_reply = call_gm(build_summary_prompt(old_messages))
        summary_text = summary_reply.strip()
        if summary_text:
            session_data["summary"] = summary_text
    except Exception as exc:
        logging.warning(f"[摘要] 生成失败，本回合改为直接截断: {exc}")
    session_data["messages"] = session_data["messages"][-40:]
```

两个设计说明一下。丢老消息只丢前面二十条，保留最近四十条当缓冲带，真被压进摘要的都是确实有年头的剧情。`try` 包住整个摘要调用，这是故意降级：摘要请求失败大不了退回纯截断，断片总比玩家点了行动却收到 500 报错强。

生成的摘要存进 `summary` 字段，之后每次拼系统提示词都挂在角色卡后面：

```
if summary:
    system_prompt += (
        f"\n\n【前情摘要】这局早些时候发生过：{summary}\n"
        f"续写时请保持与摘要一致，别再重复已经结束的段落。"
    )
```

一句话的记忆替代二十条对话的记忆，伏笔这根线就算接上了。

## 五、存档系统里我设防的四个细节

这套游戏把 JSON 文件当存档用，目录里跑着跑着就多出一堆 `2026-10-29_13-42-24_563661.json`。读写代码不难，难的是几个边角，我一个个都埋了防线。

第一道在读编码上：

```
with open(get_save_file(session_id), "r", encoding="utf-8-sig") as f:
    return json.load(f)
```

写的时候用的是 `utf-8`，读的时候我却写的是 `utf-8-sig`。因为我某天打开存档列表全红了，查下来是有个文件开头多了三个 BOM 字符，`json.load` 直接炸。`utf-8-sig` 两头兼容：有 BOM 帮你吃掉，没 BOM 也照常读。成本一个单词，换存档永不被三个不可见字符废掉。

第二道在列存档上。列表要逐个打开 JSON，一个坏档不能让整页陪葬：

```
        except (json.JSONDecodeError, KeyError) as exc:
            logging.warning(f"[存档] {save_file.name} 读取失败，已跳过: {exc}")
            continue
```

单文件解析失败或字段缺失，记条日志跳过它，其他存档照常列出来。

第三道在删存档上。删除接口是路径穿越的重灾区，万一有人把 `session_id` 传成 `../../某目录/重要文件`：

```
    save_file = get_save_file(session_id)
    if save_file.parent.resolve() != SAVES_DIR.resolve() or save_file.suffix != ".json":
        return ApiResponse(code=400, message="存档名不合法", data=None)
```

拼出来的最终路径 resolve 之后必须还落在 saves 目录里，而且后缀必须是 `.json`，两个条件任何一个不过直接拒。能删的永远只有自家存档。

第四道在 HP 归零上。玩家死了继续输行动，后端不能陪他玩下去：

```
    if session_data["character"]["status"]["hp"] <= 0:
        return ApiResponse(
            code=409,
            message="角色已死亡，无法继续本局，请读取存档或重新开始",
            data={"dead": True, "character": session_data["character"]},
        )
```

死亡状态是存档里的事实，请求还得继续推演就属于撒谎。409 把门拒了，具体前端怎么接这个码，留到下一篇讲界面时收。

## 六、还剩最后一块拼图

后端到这里功能上是全的了：推演、记账、记忆压缩、存读删都立住了。但我打开浏览器看它，还是一口 JSON 的原始样子，没有建卡页，没有状态面板，死了也只是接口里多一个字段。

最后一篇讲前端：一个 `index.html` 加一个 `game.js`，我怎么把这套后端穿成一个能点着玩的游戏，以及收官时回头看，这个项目比猜字谜那次多学会了什么。
