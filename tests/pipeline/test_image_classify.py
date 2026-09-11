from pipeline.image_classify import (
    LIFESTYLE_STD_MIN,
    PACKSHOT_STD_MAX,
    classify_std,
)


def test_confident_packshot_below_threshold():
    label, confident = classify_std(0.0)
    assert label == "packshot"
    assert confident is True

    label, confident = classify_std(PACKSHOT_STD_MAX)
    assert label == "packshot"
    assert confident is True


def test_confident_lifestyle_above_threshold():
    label, confident = classify_std(LIFESTYLE_STD_MIN)
    assert label == "lifestyle"
    assert confident is True

    label, confident = classify_std(150.0)
    assert label == "lifestyle"
    assert confident is True


def test_ambiguous_band_proposes_but_not_confident():
    midpoint = (PACKSHOT_STD_MAX + LIFESTYLE_STD_MIN) / 2

    label, confident = classify_std(PACKSHOT_STD_MAX + 1)
    assert confident is False
    assert label == "packshot"  # just above the packshot cutoff, below midpoint

    label, confident = classify_std(LIFESTYLE_STD_MIN - 1)
    assert confident is False
    assert label == "lifestyle"  # just below the lifestyle cutoff, above midpoint

    label, confident = classify_std(midpoint)
    assert confident is False
