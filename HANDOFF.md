# RAGLearn 当前状态

更新：2026-10-28（Asia/Shanghai）。单一学习路线；长期规则见 [AGENTS.md](AGENTS.md)。

## 当前阶段与下一步

Chroma 基础阶段按用户操作反馈结束：建库、迁移向量、连接、查询和 return hits。现在进行基于真实 Obsidian 笔记的分块设计，继续由用户自己写脚本、安装和运行；助手负责流程、参考代码、解释与记录。

**当前第一入口：[OBSIDIAN_RAG_V2_GUIDE.md](docs/OBSIDIAN_RAG_V2_GUIDE.md)。** 已按用户要求交付完整实操教程及五个完整参考脚本，由用户自己创建、运行；当前 note_parser_v2.py 已由用户创建，助手未改。覆盖副本、解析/预览、首次建库、增量同步、检索与父上下文、增删改练习、CPU 验收、可选问答和选定 Vault 目录接入。

用户补充“未来会频繁加入新笔记”，因此日常更新已改为 prepare + sync：同一 collection 增量计算新 ID 的向量、更新关联与位置、删除消失 ID；换模型或解析契约再用新集合。当前不是文件级解析缓存或后台服务。用户已自行创建 note_parser_v2.py，本轮保留，未审查或运行。

用户随后明确委托助手选择并准备 data/obsidian_v2_sample/ 副本，现已完成：18 篇全文复核、完整 kb.py stdout 17,730/24,000 字符，2 篇保守敏感模式命中而跳过；16 篇按原相对路径原样复制，共 17,038 字节，源/副本 SHA-256 全部一致，未覆盖已有文件。清单与预览检查目标见 [OBSIDIAN_V2_SAMPLE.md](docs/OBSIDIAN_V2_SAMPLE.md)。仅本地 .git/info/exclude 新增样本目录规则，16 份副本 check-ignore 通过。此授权限于副本准备，未运行分块、向量化或数据库同步；下一步由用户完成教程第 3～4 节及后续验收。

[OBSIDIAN_CHUNKING_DESIGN.md](docs/OBSIDIAN_CHUNKING_DESIGN.md) 保留设计与样本证据；旧 [OBSIDIAN_RAG_GUIDE.md](docs/OBSIDIAN_RAG_GUIDE.md) 只作 v1 对照。真实笔记解析、BGE 推理、Chroma 同步、CPU 速度和问答质量均未由助手运行验收。

用户明确纠正“限制读取 Vault 的规则不是其亲自编写”，并授权查看真实仓库，随后要求多看样本、深入思考和做好记录。本任务的只读审阅已经获得授权，无需重复询问；不扩大为改笔记、建库、下载模型或额外模型问答。

## 最新审阅证据

- 允许范围的文件元数据计数：325 个 Markdown，其中日记 129；按 personal-obsidian 白名单、排除目录/链接/嵌套仓库规则，不是全 Vault 总数。
- 本次扩大读取预算至 80,000 字符，实际 43 个不同文件、47 次 kb.py read，完整 stdout 累计 77,224 字符；26 个全文、17 个局部，4 个长文件另补读中段。正文读取已停止。
- 覆盖 16 篇 2026 年 3～10 月日记/周记，以及各普通笔记目录、根普通笔记和剪藏；按月份/长度/结构有目的选样，不是随机全库调查。附录逐文件记录路径、已读行范围、全文/局部和字符计量，不保存正文或敏感值。
- 前轮读过另外 3 个样本：2026-04-08 日记、2026-06-03 日记、et agent 8999 端口笔记；4 次 read、stdout 10,651 字符。这些不混入本次 43 个/77,224 的统计。
- 样本发现：空模板/占位、纯链接、通用标题下混话题、任务多日期、长代码和异常围栏、标注不准确/不完整的代码、整页 HTML/CSS、长 URL、表格、引用对话、全局静态证据边界、敏感字段。
- 这些是当前源文本结构的证据；没有核验笔记技术方法的当前有效性，没有对全库做正文统计、敏感扫描、去重或 token 分布测量。

## 当前设计决策

- 沿用 BAAI/bge-small-zh-v1.5、CPU，不因文档类型复杂就先换模型。候选模型需要性能与质量实测。
- v2 首选“格式识别/检索视图整理 → 局部理解单元 → 较小检索块 → 关联回取上下文”。保留源位置与清洗映射。
- 日记通用标题不作主题保证；任务父子项、正误示例、解释/代码/输出、前提/现象/结论要保持关系。超长代码可选 AST，失败降级，不执行。
- 全局文档前提单独关联；上下文有预算，不能把整个混话题日记自动展开。缺必要条件时标记不完整。
- 首轮检索输入仍用 320-token 总预算作实验起点，父上下文约 800～1200 tokens 仅为阅读预算建议，尚未实测。不是最优值或 Codex 的实际 token 计量。
- v2 文档代码已使用 markdown-it-py/PyYAML；整页 HTML、未闭合围栏、疑似敏感文件先诊断并跳过。复杂语义分类、链接解析、OCR 未实现；代码 AST 失败回退分段，但未单独输出每块解析状态。
- 敏感字段在普通正文也出现；不能只排除 credentials 文件，也不能只脱敏 embedding 而让 documents/父上下文/预览泄漏原值。未处理的单元先不索引并报告。
- 用户不用人工逐篇分块，也不用准备完整问答配对；已知原文位置用于局部验收，未知答案的查询只评价有用程度，不声称完整召回。
- 源 Vault 不改写；首次用明确选择的副本和独立集合。日常新快照同步同一集合；来源根/模型/解析器改变时另建集合。检索不授权向云端发送任意原文或写回笔记。
- 子块 ID 基于来源、编码文本与重复出现序号；父/行号只变化则更新 metadata。每次 prepare 重新扫描/解析允许范围，仅 embedding 和数据库按差异处理。
- 保留不可变快照；latest 指向最新预览，collection metadata 指向最后已提交快照。sync_status=updating 时拒绝查询，中断后重跑恢复，不是假定跨文件/Chroma 原子事务。教程要求顺序单进程操作。

## 已有产物与验证状态

- 新增 docs/OBSIDIAN_CHUNKING_DESIGN.md：审阅依据、v2 算法取舍、最小范围、数据契约、16 类验收与 43 个样本覆盖记录。
- 新增 docs/OBSIDIAN_RAG_V2_GUIDE.md：note_parser_v2.py、prepare_notes_v2.py、sync_notes_v2.py、search_notes_v2.py、ask_notes_v2.py 五个完整参考模块及一个配置替换片段，均仅在文档中。
- 更新 v1 教程、设计文档、学习笔记与本文件的当前入口/更新策略，保留旧参考代码和样本证据。
- v1 前轮验证：5 个 Python 代码块 AST、12 个 PowerShell 代码块 AST、6 个合成分块检查及 6 个 mock 检索/问答预览检查通过。没有真实 tokenizer、模型、数据库、笔记检索和问答运行证据。
- v2 检查通过：五个完整模块和一个配置片段 AST；17 个 PowerShell 块 Parser.ParseInput；7 份 Markdown 的本地链接/围栏及 git diff --check。审阅附录此前核对为 43 文件、47 次、26 全文/17 局部、77,224 字符，未再读真实 Vault。
- v2 共 21 项合成检查通过：实际 Markdown/YAML 解析、长代码内容保留、表格源范围、任务/正误上下文、占位与链接/插件、敏感/HTML/异常围栏、扫描边界、首次/零变化同步、仅行号变化复用向量、新增修改改名删除、契约与来源变化拒绝、中断恢复、提交快照绑定、过滤/模型复用、同步期间拒查、超长上下文标记、默认不调用云端及父 ID 分隔歧义回归。
- 测试仅使用临时目录中的虚构笔记、真实已有解析库、假 tokenizer/模型/Chroma/Codex。没有真实 BGE/数据库/API 调用，不能当作真实端到端验收。助手未在项目根创建或执行参考脚本。
- 官方参考已核对：markdown-it-py token/语法树与源行 map、Python HTMLParser/AST、层级/窗口检索思路；未因此安装依赖。
- 此前教程阶段未改业务脚本、源笔记、数据/数据库或依赖；本次另获选样授权后仅增加上述 16 份 data/ 副本及本地忽略规则。AGENTS.md、业务脚本、Vault、数据库和依赖仍未改；未 commit/push、未运行 Codex 问答。

## 环境与用户文件

- 版本证据：本轮查得 Python 3.12.3、markdown-it-py 4.2.0、PyYAML 6.0.3、sentence-transformers 6.1.0、chromadb 1.5.9；较早查得 numpy 2.5.4、transformers 5.20.2。没有加载实际模型、打开实际数据库或重新核对 CLI 登录，也没有安装依赖。
- 用户已有 build_index.py、search.py、ask.py、import_chroma.py、search_chroma.py、inspect_chroma.py。ask.py 仍从 search 导入 retrieve；ask_chroma.py 未找到。
- 上轮 index/ 快照为 3 个 chunk、(3, 512) float32、归一化；本次未重读，不作为当前实时证据。
- 已知无关问题保留：build_index.py 后缀集合 {'.txt', 'md'} 跳过 .md；import_chroma.py 重复 ID 报错文字不符且缺 np.isfinite；旧 .gitattributes 有 torch DLL LFS 规则。本轮不修。
- 本轮初始状态已有本会话文档修改：HANDOFF.md、docs/LEARNING_NOTES.md、未跟踪 docs/OBSIDIAN_RAG_GUIDE.md；均保留。不读取或清理 _temp/。

## 文档入口

- [OBSIDIAN_V2_SAMPLE.md](docs/OBSIDIAN_V2_SAMPLE.md)：已复制的 16 篇样本、选择理由与预览检查目标。
- [OBSIDIAN_RAG_V2_GUIDE.md](docs/OBSIDIAN_RAG_V2_GUIDE.md)：当前完整实操，含频繁新增的增量更新，优先阅读。
- [OBSIDIAN_CHUNKING_DESIGN.md](docs/OBSIDIAN_CHUNKING_DESIGN.md)：当前分块方案与证据，优先阅读。
- [OBSIDIAN_RAG_GUIDE.md](docs/OBSIDIAN_RAG_GUIDE.md)：旧 v1 学习对照，不是 v2 实现。
- [LEARNING_NOTES.md](docs/LEARNING_NOTES.md)：概念与阶段总结。
- [CHROMA_GUIDE.md](docs/CHROMA_GUIDE.md)：数据库阶段全流程。

下一步由用户按完整 v2 教程创建并运行脚本，先验收副本解析/预览，再建库、检索和更新，最后可选问答。不得把文档代码、合成或 mock 验证写成真实执行成功。
