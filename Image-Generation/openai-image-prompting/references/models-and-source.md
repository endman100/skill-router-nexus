# 参数与来源

核对日期：2026-09-10。来源：[OpenAI Image prompting](https://developers.openai.com/api/docs/guides/image-prompting)。以下为技术字段备忘；实际调用前重新核对当前文档和工具 schema，不从显示名称推测模型 ID。

## 参数备忘

| 模型 | quality | input_fidelity |
|---|---|---|
| gpt-image-2.5-flare / gpt-image-2.5-sunburst | auto、low、medium、high、xhigh、max | 查当前 schema，不从旧版继承 |
| gpt-image-2 | auto、low、medium、high | 省略 |
| gpt-image-1.5 / gpt-image-1 | auto、low、medium、high | low / high，按需确认 |

GPT Image 2.5 自定义宽高须为 16 的倍数，各边至多 3840，长短边比不超过 3，总像素为 655360 至 8294400；超过 3686400 像素属实验范围。GPT Image 1/1.5 尺寸为 auto、1024x1024、1024x1536、1536x1024。不同模型不能照搬参数。

透明输出使用 background=transparent 和 PNG 或 WebP；output_compression 不用于 PNG。检查 alpha 数据，不能凭棋盘格外观判断透明。

用户问模型选择、迁移、价格或停用日期时回查官方来源。这里不自动更改用户模型或设置。

## 调用前填写

```text
运行表面：{宿主图片工具 / 用户指定 API}
支持字段：{从工具 schema 或当前官方 API 文档核对}
模型：{已确认可用的 ID，或“由宿主决定”}
尺寸与格式：{用户需求与接口共同支持的值}
参考图顺序：{实际文件与 prompt 图号逐一对应}
调用范围：{生成数量、修订轮数}
```

API 集成参阅 [Image generation](https://developers.openai.com/api/docs/guides/image-generation)。不要写入密钥，不因用户只要求提示词就调用 API。

## 按任务回查原文

在主来源定位：生成看 Generate images；翻译、换装、合成、草图和去背看 Edit images；系列图看 Refine an image across turns；家具、贺卡和商品看 More workflows；结果检查看 Check the result；参数差异看对应模型 reference 标签页。

页面默认标签与示例代码可能使用不同模型。记录实际阅读标签，按所用模型核对，不将示例限制推广到所有模型。更新本文件时同步更新日期；离线无法复核时说明采用该日期备忘。
