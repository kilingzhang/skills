# Plain-Language Vocabulary & Replacement Guide (ZH + EN)

> **Core Principle**: The same buzzword can hide different engineering facts depending on the sentence. Never run blind global search-and-replace. Read the sentence, identify *who* does *what* under *which condition* (or *which field* decides the behavior), and rewrite it directly in plain Chinese or plain English.

---

## Part A — Chinese Jargon Vocabulary (Keep Replacements Natural in Chinese)

### A1. Tier-1 Chinese Jargon (Replace on Sight)

| Banned Term | Contextual Plain-Chinese Replacements |
| :--- | :--- |
| **门禁** | CI / commit checks -> `检查`, `校验`, `准入条件`; human approval step -> `人工确认`, `审批步骤`; access control -> `授权要求` |
| **收口 / 收束** | Lifecycle completion -> `结束`, `完成`, `处理完毕`; consolidating entrypoints -> `统一归入`, `汇总到`, `只保留单一入口` |
| **兜底 / 兜住** | Fallback handling -> `默认处理`, `回退逻辑`, `备用方案`; default value -> `默认值`; test/check coverage -> `拦住`, `覆盖`, `防止漏掉` |
| **口径** | Calculation formula -> `计算方式`, `统计规则`; timestamp representation -> `时区`, `时间格式`; criteria -> `判断标准`; wording -> `说明`, `定义` |
| **权威源** | Canonical doc/config location -> `唯一维护位置`, `唯一数据源`, `正式定义文件` |
| **班车** | Scheduled release -> `定时发布`, `固定批次`, `周期任务` |
| **心智** | UX / product comprehension -> `用户理解`, `使用习惯`, `理解成本` |
| **体感** | Performance / UX feel -> `实际体验`, `响应速度`, `直观感受` |
| **透出 / 可感知** | UI display / API exposure -> `显示`, `展示`, `返回给前端`, `用户可见` |
| **拉齐** | Multi-system / schema sync -> `统一`, `核对一致`, `同步更新` |
| **抓手 / 赋能 / 组合拳 / 打法** | Delete the buzzword; name the concrete tool, API, config option, or sequence of steps |
| **颗粒度 / 卡点 / 反哺 / 背书 / 痛点** | Rewrite respectively as: `细化程度（粒度）`, `阻塞问题`, `回传/补充更新`, `验证确认/签名证明`, `常见问题/不便之处` |

### A2. Tier-2 Chinese Terms (Check Context vs. Legitimate Engineering Usage)

| Term | Jargon Usage (Rewrite) | Legitimate Literal / Technical Usage (Keep) |
| :--- | :--- | :--- |
| **收敛** | `等待依赖收敛` -> `等待依赖全部就绪`; `把散落的逻辑收敛到 service` -> `把分散逻辑合并到 service`; `错误码收敛` -> `统一错误码` | Mathematical / loss / series convergence (`级数收敛`, `算法收敛`, `损失收敛`, `梯度收敛`); literal script names like `verify_loss_convergence.py` |
| **权威** | `sequence > 0 是正文权威` -> `正式正文以 sequence > 0 为准`; `选路权威` -> `决定运行路径的字段`; `权威契约` -> `正式接口文档` | Certificate Authority (`证书颁发权威`), external standards bodies |
| **对齐** | `先对齐需求` -> `先核对需求`; `字段与后端对齐` -> `字段与后端保持一致` | Layout & memory alignment: `左对齐`, `右对齐`, `居中对齐`, `两端对齐`, `基线对齐`, `像素对齐`, `字节对齐`, `内存对齐`, `文本对齐`, `图标对齐`, `网格对齐` |
| **沉淀** | `把会话记录沉淀到数据库` -> `把会话记录保存到数据库`; `沉淀排障经验` -> `整理记录排障经验` | Physical / chemical precipitation (`化学沉淀`, `沉淀物`) |
| **闭环** | `完成增删改查最小闭环` -> `走完增删改查完整流程`; `至少完成以下闭环` -> `至少完成以下验证` | Control-theory closed-loop (`闭环控制`, `PID 闭环`) |
| **水位** | `上下文基线水位` -> `上下文体积上限/基线标准`; `告警水位` -> `告警阈值` | Physical water level (`江河水位`, `水库水位`); for memory/queue metrics prefer `占用率`, `堆积量`, `阈值` |
| **底座** | `统一技术底座` -> `统一底层服务 / 基础设施` | Physical hardware stand/base (`充电底座`, `支架底座`) |
| **账本** | `运行状态账本 / 恢复账本` -> `运行状态记录 / 恢复记录表` | Actual financial accounting ledgers or blockchain distributed ledgers |
| **护栏** | `加上安全护栏` -> `加上安全校验 / 限制条件` | Physical guardrails |
| **下沉 / 打通** | `通用逻辑下沉` -> `通用逻辑抽到下层/公共包`; `打通鉴权链路` -> `接通鉴权流程` | Concrete network reachability checks (`连通`) |

### A3. Chinese Before / After Examples

- **NO**: `只有 online 不代表运行时收敛，需等待人工门禁放行后直到停止收口。`
- **OK**: `只有 online 不代表运行时所有依赖已就绪，需等待人工确认通过后直到停止完成。`

- **NO**: `本仓库是所有用户文档的唯一权威源，避免跨环境兜底与时间口径不一致。`
- **OK**: `本仓库是所有用户文档的唯一维护位置，避免跨环境回退与时间时区不一致。`

- **NO**: `工作区用于围绕一个需求持续沉淀会话和任务，把错误原因透出给用户感知。`
- **OK**: `工作区用于围绕一个需求持续保存会话和任务，把错误原因直接显示给用户。`

---

## Part B — English Jargon & AI-Cliche Vocabulary

> **Identifier Safety**: Never rename code identifiers, JSON keys, CLI flags, package names, or inline backtick references (e.g., `` `source_of_truth` ``, `` `guardrails` ``). Only rewrite prose in docs, comments, prompts, and user-facing strings.

### B1. Tier-1 English Jargon (Replace on Sight in Prose)

| Banned Term / Phrase | Plain-English Replacements |
| :--- | :--- |
| **single source of truth / source of truth / authoritative source / SSOT** | `primary record`, `canonical file`, `maintained only in ...`, `determined by ...` |
| **close the loop / closing the loop** | `complete the workflow`, `finish verification`, `report back the result` |
| **mental model** | `how users understand ...`, `expected behavior`, `concept` |
| **pain point(s)** | `problem`, `limitation`, `common failure` |
| **empower(s / ed / ing / ment)** | `let`, `allow`, `enable` |
| **synergy / synergistic / synergize** | `combined effect`, `working together` |
| **paradigm shift** | `major change`, `redesign` |
| **north star** | `primary goal`, `target design` |
| **low-hanging fruit** | `quick fix`, `straightforward change` |
| **move the needle** | `make a measurable difference`, `improve <metric>` |
| **actionable insight(s)** | `concrete finding(s)`, `specific next step(s)` |
| **best-in-class / world-class / game-changer / cutting-edge** | Delete marketing puffery or state the exact measurable behavior |
| **delve / tapestry / a testament to** | `inspect`, `examine`, `shows` |
| **corporate idiom (circle back / boil the ocean / double-click on)** | `revisit`, `do everything at once`, `inspect closely` |
| **gatekeep / gatekeeper / gatekeeping** | `restrict access`, `validation check`, `approval step` |

### B2. Tier-2 English Metaphors (Check Context)

| Term | Jargon Usage (Rewrite) | Legitimate Technical Usage (Keep) |
| :--- | :--- | :--- |
| **guardrail(s)** | `add guardrails to the prompt` -> `add validation rules / explicit constraints to the prompt` | Named external product/API features (e.g., AWS Bedrock Guardrails) |
| **leverage(s / d / ing)** | `leverage Redis to cache tokens` -> `use Redis to cache tokens` | Financial / debt leverage |
| **holistic(ally)** | `a holistic view of sessions` -> `a complete / end-to-end view of sessions` | — |
| **seamless(ly)** | `seamlessly switch workspaces` -> `switch workspaces automatically / without manual steps` | Literal texture/graphics rendering without seams |
| **blast radius** | `limit the blast radius of a change` -> `limit affected modules / impact scope` | Literal physical explosion radius |
| **escape hatch** | `provide an escape hatch for admins` -> `provide a manual override option for admins` | Literal emergency exit |
| **first-class citizen** | `treat tasks as a first-class citizen` -> `support tasks directly as a built-in resource` | Programming-language theory (`first-class functions`) |
| **footgun / silver bullet / band-aid** | `avoid config footguns` -> `avoid error-prone config options`; `band-aid` -> `temporary workaround` | — |
| **tribal knowledge** | `eliminate tribal knowledge` -> `document unwritten operational steps` | — |

### B3. English Before / After Examples

- **NO**: `This repository serves as the single source of truth to empower developers to seamlessly close the loop with guardrails.`
- **OK**: `User documentation is maintained only in this repository so developers can complete verification with automated checks.`

- **NO**: `We leverage Redis to address latency pain points and align the user's mental model.`
- **OK**: `We use Redis to reduce slow responses and make behavior match what users expect.`
