# GAOKAO-Bench attribution

The file gaokao_poetry.json is an unchanged copy of:
https://github.com/OpenLMLab/GAOKAO-Bench/blob/main/Data/Subjective_Questions/2010-2022_Chinese_Language_Ancient_Poetry_Reading.json

Project: https://github.com/OpenLMLab/GAOKAO-Bench
License: Apache License 2.0; see GAOKAO_BENCH_LICENSE.txt.
Authors cited by the upstream project: Xiaotian Zhang, Chunyang Li, Yi Zong, Zhengyu Ying, Liang He, Xipeng Qiu.
Reference: Evaluating the Performance of Large Language Models on GAOKAO Benchmark (2023).

This application extracts teaching directions from the published question, answer, and analysis fields. Those derived directions are not AI output and are not official exam annotations. The upstream dataset's source labels and scores are preserved; provenance and correctness must be checked by teachers. No claim is made that all textbook versions, years, or papers are included.

## Additional unchanged GAOKAO-Bench snapshots

The following files use the same upstream Apache-2.0 license and attribution:

- gaokao_classical.json: Data/Subjective_Questions/2010-2022_Chinese_Language_Classical_Chinese_Reading.json (29 records)
- gaokao_literary.json: Data/Subjective_Questions/2010-2022_Chinese_Language_Literary_Text_Reading.json (29 records)
- gaokao_practical.json: Data/Subjective_Questions/2010-2022_Chinese_Language_Practical_Text_Reading.json (24 records)

The local bank splits passages from question groups where recognizable; the original snapshots are unchanged and source metadata is retained. Knowledge tags are rule-derived from published analyses and need teacher review. An exam question group is not automatically assigned an official difficulty level.

## chinese-poetry

- Source: https://github.com/chinese-poetry/chinese-poetry/blob/master/全唐诗/唐诗三百首.json
- Original file: tang_poems.json, retained unchanged (366 entries).
- Copyright (c) 2016 JackeyGao. MIT license retained in CHINESE_POETRY_LICENSE.txt.
- 365 entries are added to the supplemental bank; the copy of 登高 is excluded because the curated library already includes the work. Original character forms and source topic tags are retained. These are supplemental public works, not a verified list of all high-school textbook selections. Many have no exercise/annotation.


## Additional public-domain original selections and reading guides

`curriculum.json` adds source-attributed original texts/selections only, without modern textbook notes, teaching prompts, illustrations or translations. Source, reading location, rights scope and verification status are stored per item. Classical selections from chinese-poetry retain its existing MIT attribution. Laozi chapter originals are extracted from https://github.com/hailiang-wang/book-of-tao/blob/master/src/ch2.md ; its modern translations and commentary are not copied. Variant wording is retained and labelled.

`authored_analysis.json` contains application-authored, teacher-review-required analysis drafts. `reading_guides.json` contains original study guides for entries whose original text is not embedded. A guide is not an original passage, is not a verified quotation, and cannot silently create a confirmed knowledge point. No protected modern text is replaced by a fabricated original.

## Additional objective reading snapshot

`gaokao_modern_objective.json` is the unchanged source file:
https://github.com/OpenLMLab/GAOKAO-Bench/blob/6dbb24f8d8439041e5431c4c184a582182a6ce9c/Data/Objective_Questions/2010-2022_Chinese_Modern_Lit.json

The application derives 28 distinct reading packets and 84 individual multiple-choice records from 29 upstream groups, retaining numbered answer alignment, source analyses and original score values. See `expansion_manifest.json` for the audit. Apache-2.0 and the attribution above apply. The 2023/2024 Updates repository was inspected but is linked externally only, not redistributed in this release.

`expanded_readings.json` contains public-domain ancient originals and factual titles/bylines extracted from GuWen and chinese-poetry; it excludes GuWen's modern translation and appreciation fields. Chinese-poetry MIT attribution is preserved in `CHINESE_POETRY_LICENSE.txt`. Rules-based reading aids are application code, not claims of upstream expert annotations.
