# Ticket Index Workflow

[English](README.md) | 简体中文

**作者 / Author：** hanjiang-215

Ticket Index Workflow（票据索引工作流）是一套面向大型代码仓库中 AI 编程代理的票据驱动工作流。

核心技能 **ticket-index** 会从 Markdown 票据生成确定性的三级索引，让代理无需逐一打开所有票据，就能了解当前有哪些工作、由谁负责，以及哪些工作现在可以开始。配套技能覆盖工作定义、拆分、排序、实现和评审。

核心由 Markdown 文件和一个无第三方依赖的 Python 脚本组成。安装器和可选钩子也只使用 Python 标准库。

- 适用于任何能读取 `SKILL.md` 技能文件的代理，包括 Cursor、Claude Code、Codex，以及采用相同约定的其他代理。
- 适用于从少量到数百张票据的仓库。
- 票据 frontmatter 是事实来源；索引是确定性的派生视图；当两者不一致时，`check` 会报告问题。

## 要解决的问题

当仓库中有上百张票据时，代理需要耗费大量上下文来浏览 backlog，才能找到一项可执行任务；人工维护的摘要又很容易过时。

Ticket Index 将浏览过程分成三层：

```text
docs/tickets/INDEX.md          总览：统计、模块、可开工、阻塞项和关系
docs/tickets/modules/<id>.md   模块页：按父子层级排列的票据
.tickets/<id>.md               票据正文：唯一完整内容来源
```

读者先从总览定位候选票据，再从模块页缩小范围，最后只打开对应的票据。状态、类型、负责人、优先级、依赖、层级和统计均从票据 frontmatter 读取。人只需在 `ticket-index.toml` 中为每张票据提供两个判断：所属模块和一句话摘要。

由于输出是确定性的，`diff` 会准确显示重新生成会带来的变化，`check` 会发现过期或被手动修改的输出，生成文件不会悄悄偏离源数据。

## 快速开始

要求：Python 3.11 或更高版本（使用内置的 `tomllib`）。无需安装第三方包。

```bash
git clone <repo-url> ticket-index-skills
cd ticket-index-skills

# 将技能安装到你的仓库，并安装 Cursor 自动同步钩子
python scripts/install.py --target /path/to/your/repo --install-hooks
```

`--install-hooks` 仅适用于 Cursor。Claude Code 使用 `--agent claude`；其他代理可通过 `--skills-dir` 指定其读取技能的目录。不需要钩子时，省略 `--install-hooks`。加上 `--install-git-hooks` 可以让索引在每次合并和切换分支后自动保持最新（详见下文"生成索引的冲突处理"）。

然后在目标仓库中：

1. 运行 `/setup-ticket-workflow`。确认票据 ID 前缀和模块列表后，该技能会写入 `ticket-index.toml`、`.tickets/README.md`、`docs/agents/issue-tracker.md` 和 `docs/agents/domain.md`。
2. 用 `new-id` 生成票据 ID（见命令参考），然后按 frontmatter 约定在 `.tickets/<id>.md` 下添加票据。
3. 在 `ticket-index.toml` 中为每张票据添加一条 `[tickets]` 配置。
4. 生成并检查索引：

```bash
python .cursor/skills/ticket-index/scripts/ticket_index.py render
python .cursor/skills/ticket-index/scripts/ticket_index.py check
```

当索引与票据一致时，`check` 会以退出码 `0` 返回，并输出 `OK: ...`。

[`examples/demo`](examples/demo) 包含一个完整示例项目：六张票据及其已提交的生成索引。可在该目录中运行完整性检查：

```bash
cd examples/demo
python ../../skills/ticket-index/scripts/ticket_index.py check
```

## 技能一览

技能分为三层：核心导航、规划与票据生命周期，以及帮助各环节保持可靠的工程实践。

| 技能 | 层级 | 用途 |
| --- | --- | --- |
| **ticket-index** | 核心 | 生成并验证 `.tickets/*.md` 的分层索引 |
| setup-ticket-workflow | 生命周期 | 一次性配置仓库：票据目录、索引配置和领域文档 |
| to-spec | 生命周期 | 将当前对话整理为规范文档，写入 `docs/specs/`，并创建关联跟踪票据 |
| to-tickets | 生命周期 | 将规范拆分为带阻塞关系的垂直切片票据 |
| implement-spec | 生命周期 | 在一个集成分支上，按任务图实现整份规范 |
| implement | 生命周期 | 以测试驱动开发方式实现单张票据或小型任务 |
| code-review | 生命周期 | 从仓库规范和原始规范两个角度评审变更 |
| pr | 生命周期 | 编写包含验证证据和合并风险判断的 PR 正文 |
| wayfinder | 规划 | 将大型工作整理成决策地图和子票据，逐项解决 |
| grilling | 规划 | 通过访谈逐步明确设计树中的各项决策 |
| prototype | 规划 | 构建一次性逻辑或界面原型，以验证设计问题 |
| domain-modeling | 工程实践 | 在设计过程中完善 `GLOSSARY.md` 和 ADR |
| codebase-design | 工程实践 | 提供模块深度、接口、接缝和适配器的共同词汇 |
| tdd | 工程实践 | 执行红—绿—重构循环，并指导保留有价值的测试 |
| diagnosing-bugs | 工程实践 | 建立紧凑反馈循环，诊断疑难故障和回归问题 |
| writing-for-agents | 工程实践 | 编写便于代理理解和导航的技能、`AGENTS.md` 与文档 |
| handoff | 工程实践 | 将会话整理成便于下一位代理继续工作的交接文档 |

### 技能如何配合

```text
grilling ──┐
           ├─> to-spec ──> to-tickets ──> ticket-index ──> implement-spec ──> code-review ──> pr
wayfinder ─┘        (规范)     (票据)       (导航)          (执行)           (评审)
                                                        │
                                                        └─> implement（单张票据）
```

`wayfinder` 和 `to-spec` 是两种可选的起点：当目标仍不清晰时使用 `wayfinder`；当对话已经明确设计时使用 `to-spec`。两者都将结果发布到同一个票据存储。`to-tickets` 为每张票据标注阻塞关系，`ticket-index` 生成可开工任务列表，`implement-spec` 再逐张处理当前可开始的票据。

当一个设计问题适合通过交互式逻辑演示或界面方案来验证时，可在确定方案前使用 `prototype`。把验证后的结论和一次性原型的分支链接记录到对应票据中；生产分支只保留已验证的设计与实现。

其他工程实践技能是可选的，但建议在合适时使用：确定设计前运行 `grilling`，接口或接缝设计不明确时使用 `codebase-design`，实现每张票据时使用 `tdd`，遇到疑难故障或回归时使用 `diagnosing-bugs`，术语明确后更新 `domain-modeling`，创建 PR 前运行 `code-review`，修改或扩展技能时使用 `writing-for-agents`。

### 有意不纳入的内容

- **Triage（工单分诊）**：上游技能假设使用 GitHub 或 GitLab 标签和角色状态机。本工具包使用本地文件和三种状态；加入该技能会造成状态术语冲突。
- **远程任务跟踪器同步**：索引只读取本地文件。若远程跟踪器是事实来源，请先将票据导出到 `.tickets/<id>.md`；索引脚本按设计不进行网络访问。

## 生成索引的冲突处理

票据文件和 `ticket-index.toml` 是事实来源；`docs/tickets/**` 是生成输出，任何票据变更都会改写它，因此并行分支在文本层面必然在这里相撞。安装器会把生成文件从冲突面上移除：

1. `install.py` 会在 `.gitattributes` 中添加 `docs/tickets/** merge=ours`，并在本地 git 配置中注册 `ours` 合并驱动。在全新克隆的仓库里，可以执行 `git config merge.ours.driver true` 一次性注册（或重跑安装器）。
2. 合并或变基时，git 会保留**目标分支本地**的索引；只有真正的源文件冲突会出现：`.tickets/*.md` 和 `ticket-index.toml`。不要手工合并 `docs/tickets/**`，也不要直接选择某一侧的生成结果。
3. 合并者先解决源文件冲突，再运行一次 `render` 和 `check`，让合并后的索引反映双方票据，最后把源文件和重新生成的索引一起提交：

```bash
python .cursor/skills/ticket-index/scripts/ticket_index.py render
python .cursor/skills/ticket-index/scripts/ticket_index.py check
```

如果没有配置合并驱动（例如既有克隆），回退到手工流程：先解决 `.tickets/*.md` 和 `ticket-index.toml` 中的源文件冲突，运行 `render` 和 `check` 从合并后的源文件重新生成索引，再继续变基。

可选的 `--install-git-hooks` 参数把这个闭环延伸到 git 层面：它会写入 `post-merge` 和 `post-checkout` 钩子，在每次合并和切换分支后自动重新 `render`，这样别人合并进来的票据会立刻反映到你本地的索引里。安装器写入的钩子不会覆盖已有钩子，也绝不会阻塞 git 操作。

## 命令参考

在仓库根目录运行。脚本会从当前目录向上查找 `ticket-index.toml`，也支持旧路径 `docs/tickets/index.toml`。

| 命令 | 作用 |
| --- | --- |
| `check` | 验证配置、引用和生成文件；发现问题时退出码为 `1` |
| `diff` | 打印将要发生的统一差异，不写入文件 |
| `render` | 写入 `INDEX.md` 和 `modules/*.md`，并移除过期模块文件 |
| `facts` | 打印供人工决策使用的紧凑制表符分隔事实表 |
| `new-id` | 生成一个未使用的票据 id，作为并行创建票据的防撞护栏 |

对任意命令传入 `--config PATH`，可指定配置文件，而不使用向上查找。

## 仓库目录结构

```text
skills/
  ticket-index/          核心技能、脚本和可选钩子
  setup-ticket-workflow/ 仓库脚手架和本地票据跟踪约定
  ...                    其他配套技能
examples/demo/           可运行的六张票据示例及其生成索引
.tickets/                本仓库自己的票据
docs/                    概念与参考文档，以及由 .tickets/ 生成的索引
scripts/                 install.py 和 verify.py
tests/                   使用 unittest 标准库的索引脚本、钩子和安装器测试
```

## 文档

- [依赖说明](docs/DEPENDENCIES.md)：Python 版本要求、依赖清单和验证命令。
- [概念说明](docs/concepts.md)：为何索引是派生数据、模块归属、确定性和决策地图。
- [票据约定](docs/ticket-contract.md)：frontmatter 字段、状态语义、验证规则和从其他跟踪器迁移的方法。
- [配置说明](docs/configuration.md)：所有配置项、模块和票据规则、旧目录布局及常见错误。
- [工作流](docs/workflow.md)：端到端步骤、产物和多代理协作规则。

## 开发

```bash
python scripts/verify.py      # 单元测试 + 示例检查/生成/检查/差异验证
python -m unittest discover -s tests -v
```

`verify.py` 还会确保对示例连续渲染两次时第二次不产生变化，并确认没有过期的生成文件。单元测试同时会对本仓库自己的索引执行 `check`，因此修改票据或 `ticket-index.toml` 后忘记渲染会导致 CI 失败。

## 定制

- **更换代理技能目录**：使用 `install.py --skills-dir .claude/skills`。
- **更换票据 ID 格式**：修改 `ticket-index.toml` 中的 `id_pattern`；脚本只要求文件名与 frontmatter 中的 `id` 相同。
- **更换文档语言**：生成的脚手架默认使用英文，但摘要和票据正文可以使用任何语言。
- **不安装自动同步钩子**：钩子只是安全网；`diff` 和 `check` 仍是权威检查方式。

## 许可证与来源

本项目采用 MIT 许可证，详情见 [LICENSE](LICENSE)。

新增的 `codebase-design`、`diagnosing-bugs` 和 `prototype` 技能改编自 Matt Pocock 的 MIT 许可 [skills](https://github.com/mattpocock/skills)，并固定到提交 `5beb35b040e3de97e54fa9e386d7e42d15c295c2`。`pr` 技能也注明了 HumanLayer 的 Dex Horthy 所著 `show-me` 技能。来源路径和许可证声明见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)；改进建议请参见 [CONTRIBUTING.md](CONTRIBUTING.md)。
