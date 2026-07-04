---
title: 用 GitHub Pages 重启个人网站
tags:
  - Website
  - GitHub Pages
---

这个网站现在迁移到了 [TeXt](https://github.com/kitian616/jekyll-TeXt-theme) 风格的 Jekyll 主题。首页展示文章列表，简历页集中维护正式履历，博客页保留新文章和旧归档入口。

<!--more-->

## 如何新增文章

在 `_posts/` 目录中新建 Markdown 文件，文件名使用 `YYYY-MM-DD-title.md` 格式，例如：

```text
_posts/2026-07-04-my-new-post.md
```

文件顶部写 front matter：

```yaml
---
title: 文章标题
tags:
  - Tag
---
```

正文直接使用 Markdown 编写。

## 如何更新简历

编辑 `resume.md`，替换其中的教育经历、项目经历、技能和联系方式即可。

## 旧文章

旧 Hexo 文章仍保留在 `2018/`、`archives/`、`tags/` 等目录中。后续可以逐篇迁移到 `_posts/`，也可以继续作为归档入口保留。
