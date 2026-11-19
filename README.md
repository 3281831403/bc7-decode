# BC7 解码：模式、sRGB 与 mip 链

BC7 压缩纹理在 mip 链上出现色块：模式位读错、sRGB 端点按线性插值、mip 生成顺序错、法线蓝通道不重归一化、alpha 模式混用、跨块梯度不检查、非 2 幂 UV 不 clamp、mip 偏移未按块对齐、缓存按名字索引、批量转码不隔离错误。

## 目录结构

```
README.md
conftest.py
.gitignore
texture/__init__.py
texture/bc7_decode.py
tests/test_bc7_decode.py
```

## 当前状态

`texture/bc7_decode.py` 中所有函数只保留签名与文档字符串，函数体统一
`raise NotImplementedError`。`tests/test_bc7_decode.py` 有 15 个参数化用例，
初始全部失败。

## 需要修复的 10 个问题

1. 校验模式位与分区表下标
2. sRGB 端点在线性空间插值
3. 先压缩再生成 mip
4. 法线贴图蓝通道重归一化
5. 统一预乘与直通 alpha 模式
6. 块边界梯度检查
7. 非 2 幂纹理 UV clamp
8. 各向异性 mip 偏移按块对齐
9. 解码缓存按内容哈希索引
10. 批量转码错误隔离

## 验收

```bash
python -m pytest -q
```

初始应得到 `15 failed`，且没有 collection error。实现 `texture/bc7_decode.py`
后 15 条用例应全部通过。
