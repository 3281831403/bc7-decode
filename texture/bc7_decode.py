"""BC7 解码：模式、sRGB 与 mip 链。

实现 README 中列出的 10 个修复点：

1. ``validate_mode``       模式位/分区表下标校验，防止分区表越界
2. ``srgb_to_linear``      sRGB 分量转线性，端点在线性空间插值
3. ``mip_levels``          奇数尺寸下的完整 mip 级数（先压缩后生成 mip）
4. ``renormalize_normal``  法线贴图解码后重归一化（重建蓝通道）
5. ``alpha_composite``     统一预乘/直通 alpha 的合成
6. ``gradient_range``      块内梯度跨度，用于跨块边界检查
7. ``clamp_uv``            非 2 幂纹理 UV 钳制到 [0, 1]
8. ``align_mip_offset``    mip 偏移按压缩块大小向下对齐
9. ``content_key``         按内容（而非纹理名）生成缓存键
10. ``isolate_errors``     批量转码时隔离坏块，返回失败下标而不中断
"""

import hashlib
import math


# sRGB 线性化分界点（IEC 61966-2-1）
_SRGB_CUTOFF = 0.04045


def validate_mode(mode, table_size):
    """模式位必须落在分区表有效下标内。

    BC7 块的模式位用来选择分区表行；读错模式位会让下标越过分区表
    范围，产生色块。这里做显式边界校验：合法下标（``0 <= mode <
    table_size``）返回 ``True``，越界或参数非法时返回 ``False``，
    由调用方决定如何丢弃该坏块，而不是让分区表查找越界。
    """
    if not isinstance(mode, int) or isinstance(mode, bool):
        return False
    if not isinstance(table_size, int) or isinstance(table_size, bool) or table_size <= 0:
        return False
    return 0 <= mode < table_size


def srgb_to_linear(value):
    """sRGB 分量转线性值。

    支持 0..1 浮点与 0..255 整数两种输入。BC7 的端点插值必须在线性
    空间进行，否则暗部会发灰。
    """
    if value <= 0:
        return 0.0
    # 0..255 整数分量先归一化
    if value > 1.0:
        value = value / 255.0
    if value <= _SRGB_CUTOFF:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def mip_levels(width, height):
    """按奇数尺寸计算完整 mip 级数。

    每一层长宽各自向上取半（``ceil(n/2)``），直到 1×1，因此 13×7 的
    链为 13×7 → 7×4 → 4×2 → 2×1 → 1×1，共 5 个尺寸、4 次降采样。
    非正尺寸没有有效层级，返回 0，而不是裁掉奇数末层。
    """
    if width <= 0 or height <= 0:
        return 0
    levels = 0
    w, h = width, height
    while w > 1 or h > 1:
        levels += 1
        w = (w + 1) // 2
        h = (h + 1) // 2
    return levels


def renormalize_normal(vector):
    """法线贴图解码后重新归一化。

    BC7 只精确保留两个通道，蓝通道需按 ``z = sqrt(1 - x² - y²)``
    重建；整体再归一化为单位向量，避免压缩后出现硬边。
    零向量（无有效法线）原样返回零向量。
    """
    x, y, z = (float(c) for c in vector)
    norm = math.sqrt(x * x + y * y + z * z)
    if norm == 0.0:
        return [0.0, 0.0, 0.0]
    nx, ny, nz = x / norm, y / norm, z / norm
    # 由重建后的 x/y 推导蓝通道，数值钳制防止根号下出现微小负值
    b = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
    # 保留原 z 的符号约定（法线朝下的情况）
    if nz < 0.0:
        b = -b
    rebuilt = math.sqrt(nx * nx + ny * ny + b * b)
    return [nx / rebuilt, ny / rebuilt, b / rebuilt]


def alpha_composite(foreground, background, alpha):
    """按统一 alpha 模式合成颜色。

    内部一律使用直通（straight）alpha 的 source-over 公式::

        out = fg * a + bg * (1 - a)

    预乘 alpha 的纹理在调用前需先反预乘，从而避免半透明边缘发黑。
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha 必须落在 [0, 1]")
    return foreground * alpha + background * (1.0 - alpha)


def gradient_range(block):
    """块内梯度跨度，用于跨块检查。

    返回块内最大分量与最小分量之差。相邻 4×4 块做边界检查时，跨度
    突变说明块间色差被压缩放大。
    """
    values = [float(v) for v in block]
    if not values:
        return 0
    return max(values) - min(values)


def clamp_uv(u, v):
    """非 2 幂纹理 UV 采样钳制。

    非 2 幂纹理不支持 repeat 寻址，采样坐标必须钳制到 [0, 1]，
    否则边缘会采样到越界压缩块。
    """
    return [
        min(1.0, max(0.0, float(u))),
        min(1.0, max(0.0, float(v))),
    ]


def align_mip_offset(offset, block):
    """mip 偏移按压缩块大小向下对齐。

    各向异性过滤的 mip 偏移必须对齐到压缩块（BC7 为 16 字节/4 像素
    块）边界，否则不同块的纹素被混入同一采样，远处出现闪烁。
    ``block`` 非正时抛出 ``ValueError``。
    """
    if block <= 0:
        raise ValueError("block 大小必须为正")
    return (offset // block) * block


def content_key(data):
    """按纹理内容哈希生成缓存键。

    解码缓存不能按纹理名索引（同名不同内容会互相覆盖），而要按内容
    哈希索引。对内容取 ``repr`` 后做 SHA-1，取前 16 个十六进制字符
    作为 64 位缓存键；同时支持 ``str`` 与 ``bytes`` 输入。
    """
    if isinstance(data, str):
        payload = repr(data).encode("utf-8")
    elif isinstance(data, (bytes, bytearray, memoryview)):
        payload = repr(bytes(data)).encode("utf-8")
    else:
        payload = repr(data).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:16]


def isolate_errors(results):
    """批量转码返回失败下标，不中断其余纹理。

    入参为每张纹理/每个块的成功标志序列（真值为成功、假值为失败）。
    返回所有失败项下标的列表；单个坏块只记录其下标，不影响其他纹理
    的转码结果。
    """
    return [index for index, ok in enumerate(results) if not ok]
