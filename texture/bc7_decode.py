"""BC7 解码：模式、sRGB 与 mip 链：待实现的核心模块。"""


def validate_mode(mode, table_size):
    """模式位必须落在分区表有效下标内。"""
    raise NotImplementedError

def srgb_to_linear(value):
    """sRGB 分量转线性值。"""
    raise NotImplementedError

def mip_levels(width, height):
    """按奇数尺寸计算完整 mip 级数。"""
    raise NotImplementedError

def renormalize_normal(vector):
    """法线贴图解码后重新归一化。"""
    raise NotImplementedError

def alpha_composite(foreground, background, alpha):
    """按统一 alpha 模式合成颜色。"""
    raise NotImplementedError

def gradient_range(block):
    """块内梯度跨度，用于跨块检查。"""
    raise NotImplementedError

def clamp_uv(u, v):
    """非 2 幂纹理 UV 采样钳制。"""
    raise NotImplementedError

def align_mip_offset(offset, block):
    """mip 偏移按压缩块大小向下对齐。"""
    raise NotImplementedError

def content_key(data):
    """按纹理内容哈希生成缓存键。"""
    raise NotImplementedError

def isolate_errors(results):
    """批量转码返回失败下标，不中断其余纹理。"""
    raise NotImplementedError
