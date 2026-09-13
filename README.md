# experiment-report

一个 ZCode skill：把实验报告里的原始整屏截图批量整理成排版整齐的插图。

## 它解决什么问题

实验报告里经常要贴一连串终端截图。原始截图通常带着窗口边框、任务栏、
大片空白，而且每张图的命令提示符 x 坐标都不一样，竖着排起来参差不齐。

这个 skill 提供 `scripts/crop_screenshots.py`（基于 Pillow），两种模式：

- **`terminal` 模式（核心功能）** — 自动去除外围空白后，找出每张图最左侧
  的文字列，取全批的**中位数**作为基准，左侧补边使所有图的提示符落在
  同一 x 坐标上；右侧补齐到统一宽度。只补边、不缩放，等宽字体保持像素清晰。
- **`panel` 模式** — 只统一外边距（浏览器 / GUI 截图用），超过 1200px 才等比缩小。

每次运行输出：编号命名的 PNG、单文件 `preview.html` 预览、机器可读的
`crop_log.json`（每张图的裁剪框、文字起点、最终尺寸）。

## 快速开始

```bash
pip install pillow

python scripts/crop_screenshots.py \
    --input  <原始截图目录> \
    --output <输出目录> \
    --mode terminal   # 或 panel
```

常用参数：`--pad N`（外边距，默认 16）、`--bg "#RRGGBB"`（显式指定背景色）、
`--threshold N`（背景判定容差，默认 12）、`--max-width N`（panel 模式最大宽度）。

完整说明见 [SKILL.md](SKILL.md)，裁剪规则的深入解释见
[references/crop_rules.md](references/crop_rules.md)。

## 示例（examples/）

| 目录 | 内容 |
| --- | --- |
| `examples/terminal_demo/` | 5 张提示符错位、带边框杂带的仿真终端截图（input）→ 对齐后的输出（output） |
| `examples/panel_demo/` | 3 张带杂乱桌面边缘的窗口截图（input）→ 统一留白输出（output） |
| `examples/env_terminal/` | 真实案例：环境变量实验终端序列的整理结果（原始截图涉隐私，仅保留输出） |
| `examples/vpn_terminal/` | 真实案例：VPN 隧道实验终端序列的整理结果（同上） |

每个 demo 的 `input/` 可用 `scripts/make_demo_screenshots.py` 重新生成，
方便复现：

```bash
python scripts/make_demo_screenshots.py --kind terminal --out examples/terminal_demo/input
python scripts/crop_screenshots.py --input examples/terminal_demo/input \
    --output examples/terminal_demo/output --mode terminal
```

验证效果：terminal_demo 的 5 张输出，左侧文字列全部对齐到 x=16，
宽度统一为 320px（见各目录内 `crop_log.json`）。打开各 output 目录下的
`preview.html` 可直接查看堆叠效果。

## 目录结构

```
experiment-report/
├── SKILL.md                      # skill 主文档（触发条件、用法、裁剪规则）
├── scripts/
│   ├── crop_screenshots.py       # 核心批量裁剪/对齐脚本
│   └── make_demo_screenshots.py  # 生成示例输入（可复现 demo）
├── references/crop_rules.md      # 裁剪规则深入参考
├── assets/example_asset.txt      # 常用调用片段
└── examples/                     # 上述示例
```
