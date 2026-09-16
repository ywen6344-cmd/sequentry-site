# -*- coding: utf-8 -*-
"""
visibility — AI 搜索可见度采样。

采集层（collect）把「问题集 × 引擎」跑成原始回答留档；
指标层（metrics）把原始回答算成提及率、位次、引用份额和来源结构；
构建层（../build_visibility_snapshot.py）把指标压成首屏用的一个小 JS 文件。

分三层是有意的：指标定义以后会改，改了要能拿历史原始档重算。
"""
