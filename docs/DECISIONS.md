# Decision log

本仓库关键口径与协议决定的记录。每条注明**仓内依据**（文件位置或提交）与可核对的日期
（= git 提交日期，`git log` 可逐条对上）；只收当时已留下书面痕迹的决定。

## 2026-10-08/09（`8344ae6`…`ea5ec59` 发布整理）

1. **撤掉 AIGC frontmatter，改为显式的 AI 使用声明**（`8344ae6`）；图全部重画为
   无水印版本并保留可编辑矢量源（Figure 3 / OoC 决策链 draw.io，`94dc717`/`0d81136`；
   Figure 1 UMAP 用独立 Python 重渲，`fbbd9b3`）。决定动机：交付物不能带生成痕迹，
   且图必须可从仓内脚本再生。
2. **外部验证数据不随仓分发**：`cpg0016-jump` 9 块板放在仓外 workspace 根
   （SHA256 manifest，159.9 MB），仓内只留校验清单与复现命令（README §5 cross-site 条）。

## 2026-11-03（`31ca5d5`）

3. **headline 换成泄漏受控的口径**：默认分类协议定为 **soft scaffold-grouped 5-fold CV**
   （ECFP4 Tanimoto τ=0.6，同 scaffold 全部复点同折）；well-level 5-fold CV 明确标注
   "NOT the headline"——该切分下 84.6–91.4% 测试化合物同时出现在训练里，
   0.768 度量的是复点记忆而非表型（README §5）。
4. **分组方案本身作为协议对照报告**：hard-scaffold 与 fingerprint-cluster 给出
   0.5258 / 0.4775，"分组选择移动数字最多 0.048，不足以解释与随机的差距"——
   协议差不能吞掉结论（README §5；`reports/12_technical_report_draft_v7.md` §22–24）。
5. **AUC=1.0 的 treated-vs-DMSO+ECFP4 运行改定性为结构对照**：DMSO 与所有化合物
   化学隔离（平均 ECFP4 距离 0.9683），该数不作表型结果报（README §5）。
6. **跨站外推负结果如实发布**："Result: not reproduced"；并且把假象**量化**而不是
   归咎模型——8/9 块外板的全部 vehicle 孔落在两固定列（position-only CV AUC 1.0000，
   置换 p=0.0000），其高于随机的分数是列读出；布局类 pilot 的那 1 块板 0.4248–0.5543。
   同时自查出 pilot 两块板是同一阵列（384/384 化合物一致），坐标-only 模型互转
   AUC 0.7450 ⇒ **站内 0.6825 并非布局留出**（README §5；
   `reports/24_cross_site_external_validation.md`）。
7. **位置无关的迁移证据单独设臂**：只取"查询坐标处该化合物无孔"的板对，
   R@1 0.5971 [0.5488, 0.6403]（适用 null 0.0061）；并报告不同坐标臂反而**高于**
   位置匹配臂（配对 +0.0541，单侧 p=0.0057）这一反直觉方向（同上）。
8. **MOA 簇级富集与 strength–toxicity 不显著的负结果**留在技术报告透明发布，
   不提升到摘要（README §5 末条）。

## 2026-11-18（`29120d5`）

9. **引用锚定为仓库本身**（CITATION.cff + How to cite 节）；JUMP-CP 上游数据按
   其引用要求另行致谢（README §4/§8；2026-11-18 因新增 §7 External baselines，
   License/How-to-cite 顺延为 §8/§9）。

## 2026-11-19（merge `4ab6b91` 与其后的第二次 merge）

10. **整合远程新提交用 merge，不用 rebase**：判据来自仓库内部证据——
    `reports/22_optimization_log.md` 的多行写死了本地这批提交自己的短 hash
    （`6861df5`/`cad2391`/`23b8a04`/`2b45eff`/`de7a85a`/`11c5e4d`），rebase 重写
    hash 会让账本记录变成假的；merge 保持 11 个已有提交不变。第一次合并前
    `git merge-tree --write-tree` 干跑为单树零冲突，实际 merge 同样干净
    （`11 未推 + 3 远程 → ahead 12 / behind 0`）。
11. **两个撞名未跟踪文件（`CHANGELOG.md`、`docs/DECISIONS.md`）先验证再让路**：
    逐行 diff 证明 `DECISIONS.md` 与远程版全等、`CHANGELOG.md` 是远程版的严格
    子集（只少 2026-11-18 那条说明，共 4 行，无本地独有内容），故以复制而非移动到
    仓库外备份目录 `Kaggle_2026/cell-painting_backup_20261119/` 后删除工作树副本、
    由远程版接管；不存在"删了才发现本地有独有内容"的路径。四个
    「-副本202610091157…」pdf/png 继续保持未跟踪，本次仍未纳入提交。
12. **53/54 而非 54/54 如实登记，不顺手重录环境指纹**：唯一 FAIL 是
    `reports/23_environment_fingerprint.json` 中 `transformers` 记为 `None`、
    本机为 5.22.2。重录要改写一个已跟踪工件（并牵动 fingerprint 自洽测试与
    PDF 文本锚点），属独立决定，故只写进 CHANGELOG 的 Planned 与本 ledger，
    不在推送批次里附带完成（`scripts/record_environment.py` 为既定重录入口）。
13. **推送被二次拒绝对待人工折叠冲突**：第一次 merge 后 `git push` 仍报
    non-fast-forward，fetch 发现远程多出 `7e456c3`（`docs/external_baselines.md`，
    README 新增 §7）。第二次 merge 只在 `CHANGELOG.md` 与 `docs/DECISIONS.md`
    冲突（README 自动合并成功）。两处都不是取舍而是折叠：external-baseline 对比表
    从「Planned」变为已交付，故删掉本地侧那条 Planned、保留远程的交付条目；
    决定 9 的 § 引用按新章节号采用远程版。本地新增的 Stage 12–16 条目与
    10–12 条决定全部保留，没有为消除冲突而丢弃任何一侧的内容。
