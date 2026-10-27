# AGENTS.md

## 通用工作原则

- 先理解问题再实施：说明假设、歧义和取舍；关键信息不足时先问，不隐藏不确定性。
- 最小实现：不增加未要求的功能、抽象、配置或重构。
- 外科式修改：每处改动都应对应用户要求；保持现有风格，不清理无关代码、目录或用户改动。
- 目标驱动：多步骤工作给出简短计划与验收标准；修复问题先确定反例，按影响范围验证。
- 结论区分代码阅读、静态检查、用户反馈、实际运行和完整问答验收；不以一种证据替代另一种。

## 项目目的与协作方式

- 本项目用于从零理解 RAG，先跑通小规模中文资料，逐步学习向量数据库，未来再用于用户自己的 Obsidian 笔记。
- 默认用中文解释。用户亲自安装依赖、编写/修改 Python、运行命令和排错实验；助手提供完整流程、原理、参考代码、可复制的 PowerShell 命令、预期结果和验收方法。
- 用户偏好一次取得端到端流程，不将完整教程拆成需要反复催促的片段；具体问题先直接解答，再补必要细节。
- “可以接数据库”“给我全流程”等教学请求，不自动授权助手修改业务脚本、安装依赖、下载模型、写入数据库或运行模型问答。
- 用户明确要求整理规范、学习笔记和跨 session 状态时，可以编辑对应项目文档；本轮文档授权不扩大为代码或运行授权。后续明确授权可以改变协作范围。
- 只读检查限于当前问题所需的项目文件、环境和产物；不顺带扫描用户其他资料。
- 已有脚本、data/、index/ 和 _temp/ 都视为用户产物；保留现状，不擅自格式化、覆盖、重建或清理。
- 不自动 commit、push、部署、发送消息或更改登录/账号配置。

## 技术路线与数据契约

- 当前基线：项目 .venv 的 Python；本地 BAAI/bge-small-zh-v1.5；CPU；文档向量归一化；NumPy 全量余弦相似度检索。
- 文档和问题使用同一 embedding 模型、同一向量空间；查询前缀与归一化方式保持一致。维度相同不足以证明模型兼容。
- 生成阶段优先沿用用户选择的 Codex CLI 登录路径，不自行改回需要单独 API Key 的回答方案。
- Chroma 学习阶段采用本地 PersistentClient，显式传入已有 embeddings/query_embeddings，先理解存储与检索，再考虑自动 embedding、框架或服务器部署。
- 文件基线和数据库实验并存；新示例优先使用独立脚本和独立数据库目录，方便对照，不覆盖基线。
- chunk 必须保留稳定可追溯的 ID、原文和相对来源；后续接真实笔记时再设计标题、行号、更新时间、排除目录与增量更新。
- metadata.json 同时包含索引配置、chunk 原文与元数据；embeddings.npy 是向量矩阵。当前 index/ 是检索产物目录，不能据其名称宣称已建立专用 ANN 索引或向量数据库。
- 归一化点积是余弦相似度，越大越近；Chroma 配置 cosine 后返回余弦距离，越小越近。只有在该度量下才用 score = 1 - distance 对齐展示。
- 相似度不是答案正确概率。回答应依据实际检索片段标注来源；资料不足时明确说明，不编造。
- 提示词中的“不读其他文件/不调用工具”是行为要求，不等同于技术上完全禁用了工具或隔离了文件访问。
- 重跑 upsert 不会自动删除原文已消失的旧 chunk；换模型、切块策略或语料快照时明确处理旧数据。教学初期优先使用新 collection，不自动重置数据库。

## 学习与验收

- 每个阶段说明：输入、处理步骤、输出文件/字段、运行方式、预期结果、常见错误和验收标准。
- 先分别验收读取/切块、向量化、检索、数据库持久化，再验收生成；检索正确不代表回答正确，带引用不代表引用支持结论。
- 数据库练习覆盖写入与数量、按 ID 读取、相似检索、来源过滤、独立样例的增删改、进程重启后读取，以及和 NumPy 基线对照。
- 固定评估问题包含直接问法、同义问法、多来源问题和语料外问题；保持输入一致后才比较结果。
- 不因使用数据库就声称更快、更准确或已可用于个人知识库；静态通过、用户报告和实际运行结果分别记录。
- 新发现的无关问题先说明，未经授权不顺手修复；具体问题和修复验收点记录在 HANDOFF.md。

## 文档与跨 session

- 文档按读者分类：Agent 工作相关的 AGENTS.md、HANDOFF.md 保留在项目根目录；用户阅读的教程、笔记和说明统一放在 docs/ 下。新增文档沿用此分类，移动时同步更新链接、目录树和示例路径。
- 新 session 先读本文件和 HANDOFF.md，按问题查 docs/LEARNING_NOTES.md；需要具体操作时再读 docs/CHROMA_GUIDE.md 的相关章节。
- AGENTS.md：长期规则与协作边界；HANDOFF.md：当前进度、证据、未完成项与下一步；docs/LEARNING_NOTES.md：问题总结、概念和目录/文件说明；docs/CHROMA_GUIDE.md：完整数据库实验步骤与参考代码。
- 用户要求继续记录学习过程时，更新相应笔记与交接；保持简洁，不复制完整聊天或日志，不将计划写成已完成。
- 环境版本、账号状态和库 API 可能变化，必要时重新检查；不能将旧 session 的检查当作当前验证。
- 文档与示例中不写登录缓存、API Key、令牌或无关私密内容。数据库、向量、原始文本都可能包含私密信息，不能当作天然匿名数据。

<!-- personal-obsidian-route:start -->
## Personal Obsidian routing

Only when the user explicitly requests searching their personal Obsidian notes (including `$personal-obsidian` or “去我的 Obsidian 查一下”), read `C:\Users\Yihan\.codex\skills\personal-obsidian\SKILL.md` and follow it for that task. Otherwise do not search, enumerate, or pre-read the Vault at `C:\ttchina\02_Files\10_Obsidian\Yihans`. Merely discussing Obsidian is not authorization. Stop new Vault reads when requested; unrelated new questions need fresh search intent. Retrieval does not authorize note edits.
<!-- personal-obsidian-route:end -->

- “以后想接 Obsidian”是规划，不是当前读取、全库向量化、复制或上传的授权；实际接入需明确资料范围与允许的处理方式。
- 获取个人笔记用于检索，不自动授权将片段发送给云端 Codex/其他模型，也不授权写回 Vault；在接入时明确传输边界。
