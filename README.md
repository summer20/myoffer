# MyOffer

个人秋招投递信息汇总工具（单用户，本地运行或部署到 Fly.io 均可）。

## 本地运行

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/uvicorn app.main:app --reload

浏览器打开 http://localhost:8000 ，会先跳到登录页。本地开发默认账号密码是 `admin` / `myoffer`（在 `app/config.py` 里，可以用环境变量覆盖，见下）。首次启动会自动建表并灌入一份常见大厂种子数据（不含秋招链接，需要自己核实/补充）。

### 环境变量

| 变量 | 作用 | 本地默认值 |
|---|---|---|
| `MYOFFER_USERNAME` | 登录用户名 | `admin` |
| `MYOFFER_PASSWORD` | 登录密码 | `myoffer` |
| `MYOFFER_SECRET_KEY` | 登录 session 的签名密钥 | 一个不安全的开发默认值 |
| `MYOFFER_DATABASE_URL` | SQLite 数据库路径 | `sqlite:///./myoffer.db` |

**本地用默认值就行，部署到公网前必须自己设置这三个（用户名/密码/密钥）**，否则任何人都能用 `admin`/`myoffer` 登进去。

## 测试

    .venv/bin/pytest -v

## 部署到 Fly.io

前提：装好 [flyctl](https://fly.io/docs/flyctl/install/)，注册一个 Fly.io 账号。

```bash
fly auth login                                    # 浏览器登录，只需一次

fly apps create myoffer                           # 名字被占用就换一个，比如 myoffer-chenhuiying
fly volumes create myoffer_data --app myoffer --region sin --size 1
                                                    # 持久化数据卷，装数据库文件，重新部署不会丢数据

# 生产环境的账号密码/密钥，不要用本地默认值，也不要提交进 git
fly secrets set --app myoffer \
    MYOFFER_USERNAME=你的用户名 \
    MYOFFER_PASSWORD=一个只有你知道的密码 \
    MYOFFER_SECRET_KEY=$(openssl rand -hex 32)

fly deploy --app myoffer                          # 用 fly.toml + Dockerfile 构建并发布
```

部署完 `fly deploy` 会打印出访问地址（形如 `https://myoffer.fly.dev`），打开后先登录（用刚才 `fly secrets set` 的账号密码），后续每次访问都会先要求登录。

`fly.toml` 里的 `app`/`primary_region` 如果跟你实际创建的不一样，改一下这两行即可。

## Windows 版（打包成 .exe，不需要装 Python）

每次往 `master` 推送代码，GitHub Actions 会自动在 Windows 上把项目打包成 `MyOffer.exe`：

1. 打开 `https://github.com/summer20/myoffer/actions/workflows/build-windows-exe.yml`
2. 点最上面那条最新的运行记录
3. 页面往下拉到 "Artifacts"，下载 `MyOffer-windows`（是个 zip，解压出来就是 `MyOffer.exe`）
4. 双击运行——第一次 Windows 可能弹出"Windows 已保护你的电脑"（因为没有付费买证书签名），点"更多信息" → "仍要运行"即可
5. 运行后会自动打开浏览器到 `http://127.0.0.1:8000`，账号密码默认还是 `admin`/`myoffer`

### 让 Mac 和 Windows 用同一份数据

`MyOffer.exe` 默认会把数据库文件 `myoffer.db` 建在它自己所在的文件夹里。想让两台设备数据一致，靠网盘同步这个文件：

1. **两台设备都装同一个网盘同步工具**（百度网盘、坚果云等），登录同一个账号。同步工具会在本地建一个同步文件夹，例如：
   - 坚果云：Mac 上是 `~/Nutstore Files/`，Windows 上是 `C:\Users\你的用户名\Nutstore\`
   - 百度网盘：具体路径以安装时显示的为准
2. 在这个同步文件夹里新建一个子文件夹，比如 `MyOffer`
3. **Windows 端**：把 `MyOffer.exe` 放进 `<同步文件夹>\MyOffer\` 里，双击运行——它会在同一个文件夹里自动生成 `myoffer.db`，之后这个文件会跟着网盘自动同步到 Mac
4. **Mac 端**：不用挪动文件，运行时用环境变量指向同步文件夹里的那个数据库文件：

       MYOFFER_DATABASE_URL="sqlite:////Users/你的用户名/Nutstore Files/MyOffer/myoffer.db" \
       .venv/bin/uvicorn app.main:app --reload

   把路径换成你实际的同步文件夹路径即可。

**注意：不要两边同时开着跑**——用完一台就关掉，等网盘图标显示"已同步"（一般几秒到几十秒）再打开另一台。同一个 SQLite 文件被两个进程同时写，可能会冲突甚至损坏。

## 手动验收路径（每次发版前过一遍）

1. 首页能看到种子公司列表，按类型筛选可用
2. 新增一家公司，填写类型/规模标签/秋招链接，保存后出现在列表里
3. 在某公司行内点"+ 新增投递"，填岗位/base/阶段提交，该公司"投递"列计数增加
4. 打开"投递看板"，能看到刚才那条记录，行内下拉直接改阶段，保存后更新时间刷新
5. 删除一家有投递记录的公司，应先看到确认提示，确认后才真正删除
6. 打开"简历模块库"，新增一个模块（选分类、填标题、粘贴正文），保存后出现在对应分类下
7. 点"复制"按钮，能把正文复制到剪贴板（粘贴到别处验证）
8. 新增第二个同分类模块，点"上移"，顺序确实互换
9. 编辑一个模块的标题/正文，保存后立刻反映在卡片上
10. 删除一个模块，卡片消失
