import pytest

from texture import bc7_decode as mod

CASES = [
    ('validate_mode', [2, 8], True, False),
    ('validate_mode', [8, 8], False, False),
    ('srgb_to_linear', [0.5], 0.21404114048223255, True),
    ('srgb_to_linear', [0.0], 0.0, True),
    ('mip_levels', [13, 7], 4, False),
    ('mip_levels', [0, 8], 0, False),
    ('renormalize_normal', [[0, 0, 2]], [0.0, 0.0, 1.0], True),
    ('renormalize_normal', [[0, 0, 0]], [0.0, 0.0, 0.0], True),
    ('alpha_composite', [1.0, 0.0, 0.25], 0.25, True),
    ('gradient_range', [[1, 4, 2]], 3, False),
    ('clamp_uv', [1.5, -0.2], [1.0, 0.0], True),
    ('clamp_uv', [0.3, 0.7], [0.3, 0.7], True),
    ('align_mip_offset', [70, 16], 64, False),
    ('content_key', ['abc'], 'ff13f5e89c51b0b9', False),
    ('isolate_errors', [[True, False, True, False]], [1, 3], False),
]


@pytest.mark.parametrize("func_name,args,expected,approx", CASES)
def test_bc7_decode_contract(func_name, args, expected, approx):
    func = getattr(mod, func_name)
    result = func(*args)
    if approx:
        assert result == pytest.approx(expected)
    else:
        assert result == expected
