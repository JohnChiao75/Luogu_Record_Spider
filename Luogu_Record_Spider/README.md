# 洛谷记录监控器：一个轻量级的洛谷动态监控工具

![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.13+-green)
![Status](https://img.shields.io/badge/Status-开发中-orange)

## 项目简介

洛谷记录监控器是一个基于Python开发的轻量级桌面应用程序，专为洛谷（Luogu）平台的用户设计。该项目旨在帮助算法竞赛爱好者和学习者实时监控自己或他人的刷题动态，及时获取题目通过通知，并查看相关的刷题统计数据。

通过本工具，用户可以更方便地跟踪自己与好友的刷题进度，保持学习动力，同时通过数据分析了解自己的刷题习惯和薄弱环节。

## 主要功能

### 1. 自动登录系统
- **便捷登录**：只需输入洛谷账号和密码，即可一键登录
- **安全存储**：登录信息经过加密处理，保障用户账户安全
- **会话保持**：登录后保持会话状态，无需重复登录
  ![](https://cdn.luogu.com.cn/upload/image_hosting/demslpsq.png)

### 2. 监控列表管理
- **用户ID监控**：通过输入洛谷用户ID，轻松添加用户到监控列表
- **多用户监控**：支持同时监控多个用户的刷题动态
- **列表管理**：可以随时添加或移除监控用户
![](https://cdn.luogu.com.cn/upload/image_hosting/soeg8gxb.png)
### 3. 实时监控提示
- **弹窗通知**：当监控列表中的用户通过新题目时，系统会弹出桌面通知
- **即时提醒**：无需手动刷新，系统自动检测并提示新通过的题目
- **详细信息**：通知中包含用户ID、题目编号和通过时间等关键信息
![](https://cdn.luogu.com.cn/upload/image_hosting/3zvy4vwk.png)

### 4. 题目排行榜系统
- **灵活筛选**：可根据通过题目的天数范围进行筛选
- **难度分类**：支持按题目难度等级查看排行榜
- **数据可视化**：以清晰易懂的排行榜形式展示用户刷题情况
![](https://cdn.luogu.com.cn/upload/image_hosting/2zmsgjbx.png)

### 5. 用户记录查看
- **历史记录**：查看个人用户近60天的提交记录
- **提交统计**：展示通过题目数量、提交次数和通过率
- **趋势分析**：直观显示用户刷题频率和进步趋势
![](https://cdn.luogu.com.cn/upload/image_hosting/k9y190h7.png)

## 技术实现

本项目主要基于以下技术栈：
- **Python**：作为主要开发语言
- **html/css**：用于构建图形用户界面
- **Playwright**：实现爬取功能
- **ddddocr**：实现验证码识别

## 目前存在的未完善之处

### 1. 退出登录功能异常
- 当前版本中，退出登录功能存在逻辑问题
- 用户退出后，部分会话信息可能未完全清除
- 重新登录时可能出现异常情况

### 2. 界面布局问题
- 关闭窗口按钮与用户信息区域存在重叠
- 部分屏幕分辨率下界面元素显示不全
- 响应式布局需要进一步优化

### 3. 用户添加功能限制
- 目前只能通过用户ID添加监控用户，无法通过用户名添加
- 缺少用户搜索和自动补全功能
- 添加用户时缺少验证机制

### 4. 分发方式不完善
- 暂无打包的EXE可执行文件版本
- 用户需要安装Python环境才能运行
- 缺少一键安装程序和更新机制

### 5. 爬取功能不完善
- 写法较为死板，使用了XPath定位

### 6. 只支持Windows系统
- 暂未考虑兼容其他系统

## 安装与使用说明

### 环境要求
- Python 3.8或更高版本
- 稳定的网络连接
- 有效的洛谷账号

### 安装步骤
1. 克隆或下载项目代码
2. 安装依赖包：
    - pip install playwright ddddocr
    - playwright install
    - 
        命令行里输入
        ```
            python -c "import ddddocr; print(ddddocr.__file__)"
            notepad /path/to/package
        ```
        将ddddocr库中的classification函数改为
        ```
            def classification(self, img: bytes):
                image = Image.open(io.BytesIO(img))
                image = image.resize((int(image.size[0] * (64 / image.size[1])), 64), Image.Resampling.LANCZOS).convert('L')
                image = np.array(image).astype(np.float32)
                image = np.expand_dims(image, axis=0) / 255.
                image = (image - 0.5) / 0.5
                ort_inputs = {'input1': np.array([image])}
                ort_outs = self.__ort_session.run(None, ort_inputs)
                result = []
                last_item = 0
                for item in ort_outs[0][0]:
                    if item == last_item:
                        continue
                    else:
                        last_item = item
                    if item != 0:
                        result.append(self.__charset[item])

                return ''.join(result)
        ```
3. 运行主程序：`python main.py`

### 基本使用方法
1. 启动程序后，在登录界面输入洛谷账号和密码
2. 登录成功后，进入主界面
3. 在监控管理页面添加要监控的用户ID
4. 根据需要查看排行榜或个人提交记录
5. 程序将在后台自动监控并提示新通过的题目

## 未来开发计划

### 短期优化
- 修复退出登录功能异常
- 调整界面布局，解决元素重叠问题
- 增加通过用户名添加监控用户的功能

### 中期改进
- 打包生成EXE可执行文件，方便用户直接使用
- 增加数据导出功能（Excel、CSV格式）
- 添加更多统计图表和数据分析功能

### 长期规划
- 开发移动端应用版本
- 增加团队竞赛监控功能
- 集成更多OJ平台的监控支持

## 贡献与反馈

本项目目前处于开发阶段，欢迎各位开发者提出建议或贡献代码。如果您在使用过程中遇到任何问题或有改进建议，请通过以下方式反馈：

1. 在项目仓库中提交Issue
2. 通过邮件联系开发者
3. 提交Pull Request参与开发

## 注意事项

1. 请遵守洛谷平台的使用规则，不要过度频繁请求数据
2. 本工具仅用于个人学习和交流，请勿用于商业用途
3. 注意保护个人账号信息安全，不要泄露给他人

---

**洛谷记录监控器** 是一个由爱好者开发的开源项目，旨在为洛谷用户提供更好的刷题体验和数据分析工具。我们欢迎更多开发者加入，共同完善这个项目，为算法竞赛社区做出贡献。

*最后更新：2026年1月17日*