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
   其引用要求另行致谢（README §4/§7）。
