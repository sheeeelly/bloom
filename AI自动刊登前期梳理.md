## 一、方向：

新品发布流程中快速上架是业务关键动作。包含几项关键点：
### 1.标准化格式：

1.1文本信息
a.可以从图片中提取（如服装特征、面料）
b.需要人工确定（如价格）
c.标准格式可以自动化（如：标题、描述）
d.多语言翻译
1.2图片信息
a.一站式换装（正面、背面、侧面），可结合老系统[https://aigc.make234.com/#](https://aigc.make234.com/#)相关功能调用
b.选项图（自动化复色）[https://docs.zoom.us/doc/MwzAm_ieSi2dx5aZQ9SFlw](https://docs.zoom.us/doc/MwzAm_ieSi2dx5aZQ9SFlw)
### 2.迭代路径：

半自动化  → 全自动化  在推送盘古前信息抽查审核
### 3.业务承接：

承接自动化选品 [https://docs.zoom.us/doc/CU0if6VPQGW64h_pwRbHVQ](https://docs.zoom.us/doc/CU0if6VPQGW64h_pwRbHVQ)
### 4.数据回收：

4.1 回收目标：
POC阶段的数据回收，不只是记录 AI 做了哪些动作，更重要的是回答一个核心问题：AI 自动刊登是否值得继续投入资源，以及后续最值得优先投入的是哪一段能力。

4.2 核心数据回收维度：
**1.效率收益：**经调研，原上新周期约==45天==，其中30天为中山设计生产服装并完成属性表输出，15天为服装拍摄及中美两地数据审核。若采用 AI 自动刊登，预计可减少服装拍摄及审核时间约10天，上新周期可压缩至35天左右，整体==缩短约22%==。POC阶段需重点回收：单款处理时长、批量上新总周期、图片处理耗时、文本整理耗时、审核耗时等数据，验证该提效是否能够稳定复现。
**2人工介入程度：**统计自动化后仍需人工参与的环节与工作量，重点关注可节省的人力是否集中在高重复、低价值环节。当前预期可节省的人力包括：中山研发人工编写商品属性的人力、美国团队撰写商品描述的人力、上海修图人力、上海运营编辑属性并推送盘古的人力。POC阶段需回收各岗位单款耗时、参与人数、返工次数，最终形成单款节省工时和单批次节省工时的数据结论。
**3.经营结果补充：**对比 AI 刊登商品与人工刊登商品上线后的点击、转化、销售等结果，至少验证 AI 路线不会明显伤害业务表现。==（abTest数据测试）==
**4.成本收益判断：**一是周期收益，即上新周期是否从45天稳定压缩至35天左右；二是人力收益，即单款/单批次节省了多少人工工时。达到满足==周期缩短、人力下降、经营结果可接受==

4.3 阶段性判断口径：
如果 AI 在效率上有明显提升，在质量上达到可用标准，在人工投入上实现下降，且上线后的经营表现不显著差于人工刊登，则说明该方向具备继续投入和争取资源的价值。

## 二、原始业务：

### 2.1原始上新节奏


|     | 上新总数 | BD上新数量 | Atelier 上新数量 | MOB上新数量 |
|-----|----------|------------|------------------|-------------|
| 1月 |      481 |         43 |              137 |          22 |
| 2月 |      262 |         41 |               60 |           8 |
| 3月 |      595 |         61 |              223 |          19 |
| 4月 |      579 |         66 |              161 |          28 |
| 5月 |      482 |         30 |              153 |           7 |
| 6月 |      397 |         34 |              167 |           0 |

### 2.1原刊登sop

#### ==BD、JBD、mob、wd、fgd大品类==

1.上海运营有上新要求，提前==一个半月==给到中山产品研发提需。

![c1b7ed_J1rTwfYBSPq6E3W9Whsxcg_Screen_shot_1784019596273.png](https://file-paa.zoom.us/file/6Yn-ZtEITRqmSYOAYveShg?filename=c1b7ed_J1rTwfYBSPq6E3W9Whsxcg_Screen_shot_1784019596273.png&jwt=eyJhbGciOiJFUzI1NiIsImsiOiJ2dC8rcFVJKyJ9.eyJpYXQiOjE3ODQyNTQxMjAsImhkaWciOmZhbHNlLCJleHAiOjE3ODQyNTUwMjAsImRpZyI6IjU0YmU1NDZjZTY5ZWFjMDIxN2NiNzExMGRhOGZjZDAxODYzMDAzNGU4NTE4MmYwZGFjMWNlN2ViYzc1ZWI5NjMiLCJpc3MiOiJmaWxlIiwib3JpIjoibHlueC1pbnRlcmFjdGlvbiIsImF1ZCI6InpmcyIsImlpYyI6ImF3MSJ9.iEv6cQGGuFO92hI0-wFM_4UCwaLZVJuUaqLjzrQF98bFdrix1zpouJ_6wMO6CWbZSjWA85MOKuWazF7cowFw6g&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9maWxlLXBhYS56b29tLnVzL2ZpbGUvNlluLVp0RUlUUnFtU1lPQVl2ZVNoZz9maWxlbmFtZT1jMWI3ZWRfSjFyVHdmWUJTUHE2RTNXOVdoc3hjZ19TY3JlZW5fc2hvdF8xNzg0MDE5NTk2MjczLnBuZyZqd3Q9ZXlKaGJHY2lPaUpGVXpJMU5pSXNJbXNpT2lKMmRDOHJjRlZKS3lKOS5leUpwWVhRaU9qRTNPRFF5TlRReE1qQXNJbWhrYVdjaU9tWmhiSE5sTENKbGVIQWlPakUzT0RReU5UVXdNakFzSW1ScFp5STZJalUwWW1VMU5EWmpaVFk1WldGak1ESXhOMk5pTnpFeE1HUmhPR1pqWkRBeE9EWXpNREF6TkdVNE5URTRNbVl3WkdGak1XTmxOMlZpWXpjMVpXSTVOak1pTENKcGMzTWlPaUptYVd4bElpd2liM0pwSWpvaWJIbHVlQzFwYm5SbGNtRmpkR2x2YmlJc0ltRjFaQ0k2SW5wbWN5SXNJbWxwWXlJNkltRjNNU0o5LmlFdjZjUUdHdUZPOTJoSTAtd0ZNXzRVQ3dhTFpWSnVVYXFManpyUUY5OGJGZHJpeDF6cG91Sl82d01PNkNXYlpTaldBODVNT0t1V2F6Rjdjb3dGdzZnIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzg0MjU1MDIwfX19XX0_&Signature=n4LKwKx5OadwX~i3uPgmMGB5xTc-BvC-tMkxi94dOm~pIWhlN9-bpQUxNH~POBzNLoMbv~gFgwCoLZ00dg7u1WwEh-6Fc90zifHxcvy5rUlYbl9lS~qcFEN7djvdBwBLxYVsmb6WVO2sBfahME5ZDLpVjox-oPNNF8lMV0aI-GRWnJxxLGCmN-gdWD3Bt5oD833pN7qOyFoJ0fPvWoySNUN44LTRnCWq7PB7UVetRnW3cFBSx65vPCXI0KxWUJBWdbJ9i1WFGAYpbP8ClaL~Hhqq~ZCOYinC-AnIj~Jt81XKud3a0wyC9wqI86QVOnlK4lmMtR-fo~jcei3wdEz3pw__&Key-Pair-Id=KL18RPQB3R725)

2.中山产品研发提供==全套纸样====（====可外发）、激光纸样（可外发）、尺码表（可外发）、图片（可外发）、工艺备注给到工厂，工厂会负责生产==

![50a89e_f7c2a0_Screen_shot_1784020350166.png](https://file-paa.zoom.us/file/3zbS42wXS2efZmILKPmnKQ?filename=50a89e_f7c2a0_Screen_shot_1784020350166.png&jwt=eyJhbGciOiJFUzI1NiIsImsiOiJ2dC8rcFVJKyJ9.eyJleHAiOjE3ODQyNTUwMjAsImhkaWciOmZhbHNlLCJpaWMiOiJhdzEiLCJhdWQiOiJ6ZnMiLCJpc3MiOiJmaWxlIiwiZGlnIjoiMjIyOThiZjcwNmQ4YmI4YjE4YmI3YWU5N2M3Zjk4NzI1MmEyOWIzYWU4NWRiNGRjMjVhODc5ZmI0ZjViMGM4NCIsIm9yaSI6Imx5bngtaW50ZXJhY3Rpb24iLCJpYXQiOjE3ODQyNTQxMjB9.Iddw9oH5Jq66zFUPtV8JjWsyQA6Qg19_QvBq_XltNuG7GtiSdk7JhCdpL5DYsRifgWT4bQaWOsWfZvMgGaQgaA&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9maWxlLXBhYS56b29tLnVzL2ZpbGUvM3piUzQyd1hTMmVmWm1JTEtQbW5LUT9maWxlbmFtZT01MGE4OWVfZjdjMmEwX1NjcmVlbl9zaG90XzE3ODQwMjAzNTAxNjYucG5nJmp3dD1leUpoYkdjaU9pSkZVekkxTmlJc0ltc2lPaUoyZEM4cmNGVkpLeUo5LmV5SmxlSEFpT2pFM09EUXlOVFV3TWpBc0ltaGthV2NpT21aaGJITmxMQ0pwYVdNaU9pSmhkekVpTENKaGRXUWlPaUo2Wm5NaUxDSnBjM01pT2lKbWFXeGxJaXdpWkdsbklqb2lNakl5T1RoaVpqY3dObVE0WW1JNFlqRTRZbUkzWVdVNU4yTTNaams0TnpJMU1tRXlPV0l6WVdVNE5XUmlOR1JqTWpWaE9EYzVabUkwWmpWaU1HTTROQ0lzSW05eWFTSTZJbXg1Ym5ndGFXNTBaWEpoWTNScGIyNGlMQ0pwWVhRaU9qRTNPRFF5TlRReE1qQjkuSWRkdzlvSDVKcTY2ekZVUHRWOEpqV3N5UUE2UWcxOV9RdkJxX1hsdE51RzdHdGlTZGs3SmhDZHBMNURZc1JpZmdXVDRiUWFXT3NXZlp2TWdHYVFnYUEiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3ODQyNTUwMjB9fX1dfQ__&Signature=Zhwd2CSfxioqsU-iZDkoh5ZKyjeSlvGDxuZhatjnc-tgEBqezbrs5ZVPxLRTg~A1Ocxz9~6tLjwt1PYgSNf4MWWwrI2cd-UDcsAM9EBxMFFZNV9bg8ZiQ33b56WpcH-PsbDWlOcJvPuBkrfEYC5xCVOn26oci8Tc7UK-bS6IOVmASwE6ot8twI4I9zWIehM2P18LDKBralUBbhw8~Kgzm-f7Q9IPe1QP~rsB66V9SdFlvfTXbNkta3XN1o6WWyebokC9CFNOKzzE5f4romfVY0ZuexyaOrwBq5fciUxuj1-knDvLhFsNzunlipM26So~JB57IdcOeQkCu3rxAEH~7w__&Key-Pair-Id=KL18RPQB3R725)

3.工厂生产好的服装给到中山产品研发，中山产品研发整理图片和对应的属性，形成最终的属性表。

![858c5c_39867d_xM0Z9VsxT1S80uRsfsexPQ_image.png](https://file-paa.zoom.us/file/gXJWO2uESoeBtKUUuBwn0w?filename=858c5c_39867d_xM0Z9VsxT1S80uRsfsexPQ_image.png&jwt=eyJrIjoidnQvK3BVSSsiLCJhbGciOiJFUzI1NiJ9.eyJpc3MiOiJmaWxlIiwiYXVkIjoiemZzIiwib3JpIjoibHlueC1pbnRlcmFjdGlvbiIsImV4cCI6MTc4NDI1NTAyMCwiaWF0IjoxNzg0MjU0MTIwLCJkaWciOiI4MTA2YTRlOGE4N2FhY2VlYjlmZmYzNDdiNWU5ZWEwZmNlNjI1NGZjMWE0YzUzZDU0YWQ2OGMxOTZjNTI1ZTJmIiwiaGRpZyI6ZmFsc2UsImlpYyI6ImF3MSJ9.GHZWsdVNkFt4GuUACJ_B9At1U-FWhyP4p9msjNKnNUVLrfBNIa5IgWQ7xa-vP9YSodetzjnTVPG-Hm9pqxOlGw&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9maWxlLXBhYS56b29tLnVzL2ZpbGUvZ1hKV08ydUVTb2VCdEtVVXVCd24wdz9maWxlbmFtZT04NThjNWNfMzk4NjdkX3hNMFo5VnN4VDFTODB1UnNmc2V4UFFfaW1hZ2UucG5nJmp3dD1leUpySWpvaWRuUXZLM0JWU1NzaUxDSmhiR2NpT2lKRlV6STFOaUo5LmV5SnBjM01pT2lKbWFXeGxJaXdpWVhWa0lqb2llbVp6SWl3aWIzSnBJam9pYkhsdWVDMXBiblJsY21GamRHbHZiaUlzSW1WNGNDSTZNVGM0TkRJMU5UQXlNQ3dpYVdGMElqb3hOemcwTWpVME1USXdMQ0prYVdjaU9pSTRNVEEyWVRSbE9HRTROMkZoWTJWbFlqbG1abVl6TkRkaU5XVTVaV0V3Wm1ObE5qSTFOR1pqTVdFMFl6VXpaRFUwWVdRMk9HTXhPVFpqTlRJMVpUSm1JaXdpYUdScFp5STZabUZzYzJVc0ltbHBZeUk2SW1GM01TSjkuR0haV3NkVk5rRnQ0R3VVQUNKX0I5QXQxVS1GV2h5UDRwOW1zak5Lbk5VVkxyZkJOSWE1SWdXUTd4YS12UDlZU29kZXR6am5UVlBHLUhtOXBxeE9sR3ciLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3ODQyNTUwMjB9fX1dfQ__&Signature=JwvGlkUndo62h6wkEdWRWJsUC1yCiXQhXYdUHhIkgjIAIh8z1VzALkKIQQn6WLtAoNkEcTglQsQK6v87wX8~T4j1yuaIBfSTgJvSlzXvTgqF9ecr8RHZfXZ7ih9J~R62vwc9r8oLHZfruw0Ku-J5hI7I1rNrtRjFnujG4RSS~gk0CkvrlaDHh3Q7gDC~bZFsVXIQX9BFyVtPdB~Be3aHb9zzoXzjWFjVo8upRBacZuT71UBFhQFbg9CErcAhHujRhYBdbEyffLkLoJpYhNnQw6O3qF7FKgAAf1dwnlhC3ZU9ag6w6tZWc4i2JofgeZJsEtfHLjayt8T47GUsuXbeEA__&Key-Pair-Id=KL18RPQB3R725)

4.属性表会传到美国，美国那边负责写商品描述，并核对相关信息（主要是翻译的地道表达）

![image.png](https://file-paa.zoom.us/file/oV7uvRPjSiGdK7zoA4MTwg?filename=image.png&jwt=eyJrIjoidnQvK3BVSSsiLCJhbGciOiJFUzI1NiJ9.eyJhdWQiOiJ6ZnMiLCJoZGlnIjpmYWxzZSwiaWF0IjoxNzg0MjU0MTIwLCJkaWciOiIxNWJiYzI5Y2Q2NGQ0NDk1YjZkYTUzZjE3MTFjZGM1OTkxOWM4ZDA1MDM4ZDBkYTg3MjQ1NzI4MmIwNjFkMTgyIiwiaWljIjoiYXcxIiwib3JpIjoibHlueC1pbnRlcmFjdGlvbiIsImV4cCI6MTc4NDI1NTAyMCwiaXNzIjoiZmlsZSJ9.T1NNiGcWD5hOQMC_3MnG3XEH-xB2jQxQYXkcqr7F7GIKelIv6hX3i1Vb4W879E0TgRZYEQo2HW1_DrMLhTsFGA&Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDI1NTAyMH19LCJSZXNvdXJjZSI6Imh0dHBzOi8vZmlsZS1wYWEuem9vbS51cy9maWxlL29WN3V2UlBqU2lHZEs3em9BNE1Ud2c~ZmlsZW5hbWU9aW1hZ2UucG5nJmp3dD1leUpySWpvaWRuUXZLM0JWU1NzaUxDSmhiR2NpT2lKRlV6STFOaUo5LmV5SmhkV1FpT2lKNlpuTWlMQ0pvWkdsbklqcG1ZV3h6WlN3aWFXRjBJam94TnpnME1qVTBNVEl3TENKa2FXY2lPaUl4TldKaVl6STVZMlEyTkdRME5EazFZalprWVRVelpqRTNNVEZqWkdNMU9Ua3hPV000WkRBMU1ETTRaREJrWVRnM01qUTFOekk0TW1Jd05qRmtNVGd5SWl3aWFXbGpJam9pWVhjeElpd2liM0pwSWpvaWJIbHVlQzFwYm5SbGNtRmpkR2x2YmlJc0ltVjRjQ0k2TVRjNE5ESTFOVEF5TUN3aWFYTnpJam9pWm1sc1pTSjkuVDFOTmlHY1dENWhPUU1DXzNNbkczWEVILXhCMmpReFFZWGtjcXI3RjdHSUtlbEl2NmhYM2kxVmI0Vzg3OUUwVGdSWllFUW8ySFcxX0RyTUxoVHNGR0EifV19&Signature=AKEuLGHVvKWpeBrKidHYBNL-~8sSYffZxI0fU~eQbXLWmEL-qeq7BEWUyuUbniG4ck2n1gVReiRC48-di4jS98Zvo6lDgrstTQ4mGNt4ZTcuMSU2P3d0urRMtUXVEg2oWKEM9hCs9i3OUa4TrKB0qbGuz7g47JCloHrpqh5NfKPu1lJWbILH6WuS3oGZbiSyCshOtZT2KtY88ql2iScJZRd838Yn9J~NjzDJYgggERgaElkx9XDd-zIgpBNJCsWslbopXi5GVLkULOfikeGUbZIcVVTv-x3DGs~cgWH-LEvPQ3EdXD8zaOrf6OOyJqvgMnUZETDd2Ga2B5rAqdS6Lw__&Key-Pair-Id=KL18RPQB3R725)

5.上海运营拿到对应表格，上传到盘古系统。

![image.png](https://file-paa.zoom.us/file/dIVLh_6ERKy4th3wpnRreA?filename=image.png&jwt=eyJhbGciOiJFUzI1NiIsImsiOiJ2dC8rcFVJKyJ9.eyJoZGlnIjpmYWxzZSwiZGlnIjoiYmI2ZTgwODY3MmExMzdlZmJkYmU4ZWFmZDAxZDE5ZjQ5NzU4MjYwNDNhMmY1M2E1MzkyZmMyNzhjMWRhMmNlZSIsIm9yaSI6Imx5bngtaW50ZXJhY3Rpb24iLCJpc3MiOiJmaWxlIiwiYXVkIjoiemZzIiwiaWljIjoiYXcxIiwiaWF0IjoxNzg0MjU0MTIwLCJleHAiOjE3ODQyNTUwMjB9.PRtqlpsu15pPFlZQUlC28KGrYOUrx12SM-txOp3o3xCi3IqrSSu8LSVmYIJefSJfMgZUR_pZfPVlzLtbfM_6ag&Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NDI1NTAyMH19LCJSZXNvdXJjZSI6Imh0dHBzOi8vZmlsZS1wYWEuem9vbS51cy9maWxlL2RJVkxoXzZFUkt5NHRoM3dwblJyZUE~ZmlsZW5hbWU9aW1hZ2UucG5nJmp3dD1leUpoYkdjaU9pSkZVekkxTmlJc0ltc2lPaUoyZEM4cmNGVkpLeUo5LmV5Sm9aR2xuSWpwbVlXeHpaU3dpWkdsbklqb2lZbUkyWlRnd09EWTNNbUV4TXpkbFptSmtZbVU0WldGbVpEQXhaREU1WmpRNU56VTRNall3TkROaE1tWTFNMkUxTXpreVptTXlOemhqTVdSaE1tTmxaU0lzSW05eWFTSTZJbXg1Ym5ndGFXNTBaWEpoWTNScGIyNGlMQ0pwYzNNaU9pSm1hV3hsSWl3aVlYVmtJam9pZW1aeklpd2lhV2xqSWpvaVlYY3hJaXdpYVdGMElqb3hOemcwTWpVME1USXdMQ0psZUhBaU9qRTNPRFF5TlRVd01qQjkuUFJ0cWxwc3UxNXBQRmxaUVVsQzI4S0dyWU9VcngxMlNNLXR4T3AzbzN4Q2kzSXFyU1N1OExTVm1ZSUplZlNKZk1nWlVSX3BaZlBWbHpMdGJmTV82YWcifV19&Signature=KuZ4vwgAF5Akwm8glt5Xbp13qDaqqEFdjJLCa4JzUVXB3ZAV8b7ofU2rVliQZz1YhY8E07M-A-scTnCEXtpbnZsuqUICtlWzwUuq~dFop4V2M-ljzpoWag6sPfLsTNul-NA8qUErcs0bTzVl182vFdmn1tRX0yI70-n4L7S63M-FQVmx3fNH5ljNOjUHwV6ROxrSAecIkJjHExq0IVIzj-q2dJ1cBe8I-SUQAoDVo6jVifJj1iTyxd4Ust~J2klANhNEetuosWzJCDv7vLH3Sr5F6MM~caFiPlgzH65JqWILqyjLGGd95KU2mdlkiGUsllX3Qfim~AR8EEIqTuqEbQ__&Key-Pair-Id=KL18RPQB3R725)

6.修图组负责将图片上传到盘古。

#### Atelier Dresses品类

a.精品路线：与大品类一致
b.主流路线：竞品站点信息（爬虫图片+爬虫文本信息）→运营提取服装基础信息（竞品数据）→修图师修图（涉及到ai换装）→ 运营确定效果→若夫整理信息→ 推送盘古
c.供应商这边提供信息
> `运营提取服装基础信息，以Atelier表格为例：https://docs.google.com/spreadsheets/d/1Ci7jHouE7qmrhOulnd6Qy1W_cjs-TIKk7uUQEYzkH-Q/edit?gid=232172424#gid=232172424&fvid=1275754582`
> 若夫整理信息推送盘古，Atelier表格为例：
> smb://10.180.250.42/营销共享盘/AIGC/自动化刊登/in/Atelier Dresses属性录入-7.13.xlsm
#### ==prom==

新的路线：待调研
### 2.2商品运营录入表格具体标签，Atelier表格：

```plaintext
from
正面图
背面图
参考链接  
新上新日期
上新日期
商品ID
DDID
基础价格
美国售价
ERP颜色
PS团队修图参考ID
款式名称（美国团队）
商品描述（美国团队）
商品卖点详情（美国团队）
长度（美国团队）
廓形（美国团队）
袖型（美国团队）
下拉选择-品类
按场合选购（美国团队）
领型（美国团队）
装饰元素（美国团队）
产品特征（美国团队）
面料
面料克重
印花类型
日间活动场合（根据适用性选择，并兼顾SEO关键词推广）
晚间活动场合（根据适用性选择，并兼顾SEO关键词推广）
开款原因（可多选：欧洲市场、晚宴、鸡尾酒会、WGD、买手）
定制面料
主要场合（必填项）
季节（美国团队）
筛选-尺码（多选，研发填写）
长度/尾型（研发填写）
筛选-是否为大码（研发填写）
活动专题店铺
裙长
装饰
Ruofu
```
**大品类的属性表由研发填写**
#### 2.3上新业务分类

1.板房自研
2.第三方公司提供
3.竞品
## 三、自动化业务流程

### 3.1自动化路线：

a.精品路线：板房提供基础素材（模特图+文本信息）→ ai数据清洗 → ai换装 → 自动推送到盘古
b.竞品路线：竞品（图片+文本信息）→ ai数据清洗 → ai换装 → 自动推送到盘古
### 四、阶段性目标

1.原始路径自动化路径选择：选择a.精品路线 or b.竞品路线。ps精品路线无法ai换装无先例。竞品路线可以一站换装，AI接受度较大。
2.品类确定（以下几个各有优劣）：
**BD（优点：存在板房信息明确，上新数量稳定，适合poc验证；缺点：无ai换装先例）**
**MOB（优点：存在板房信息明确，上新数量稳定，适合poc验证,可以避开BD大品类；缺点：无ai换装先例，且上新数量较少）**
**Atelier （优点：部分产品已是直接ai出图,ai生图接受度较高，属性表也是运营填写，且可以避开BD大品类；缺点：上新数量较多，部分产品无板房数据，与其他品类的上新路径存在差异）**
3.时间节奏：本周完成方案和  poc验证 。
4.现状梳理和规划：现状sop流程（已完成梳理）。
5.一期方案：1.重点完成一站式换装（模特库建设）； 2.商品数据清洗，结构化输出（重点数据，待梳理）、3.部分不追求一期完全自动化，用半自动话处理。
### 五、风险点：

1.业务要求较高（可能会卡在换装效果上，需保证服装的一致性，目前业务对于ai换装不是太支持。）
2.对于属性提取需要调研，形成字典，部分信息来源多方，目前无法要到中山的资料包相关数据，不确定数据格式和清洗难度。


