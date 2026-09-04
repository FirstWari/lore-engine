"""Keyframe selection logic, exercised on synthetic images (no video decoding)."""

import imagehash
from PIL import Image, ImageDraw

from lore_engine.video import HASH_BATCH, pick_diverse


def _hash(seed: int, variant: int = 0):
    """A perceptual hash of a synthetic 'slide': seed picks the layout, variant nudges it."""
    img = Image.new("L", (128, 72), 255 - (seed * 40) % 200)
    draw = ImageDraw.Draw(img)
    for k in range(3):
        x = (seed * 17 + k * 29) % 100
        y = (seed * 7 + k * 19 + variant) % 50
        draw.rectangle([x, y, x + 25, y + 15], fill=(seed * 60 + k * 90) % 255)
    return imagehash.phash(img)


def test_keeps_first_and_drops_near_duplicates():
    # Three copies of slide 1, then a different slide 2, then slide 1 again.
    hashes = [_hash(1), _hash(1, 1), _hash(1, 2), _hash(2), _hash(1)]
    picked = pick_diverse(hashes, max_frames=10, similarity_threshold=5, min_diversity_threshold=10)
    assert picked[0] == 0
    assert 3 in picked
    assert len(picked) <= 3


def test_respects_max_frames_and_time_order():
    hashes = [_hash(i) for i in range(12)]
    picked = pick_diverse(hashes, max_frames=4, similarity_threshold=1, min_diversity_threshold=1)
    assert len(picked) == 4
    assert picked == sorted(picked)


def test_stricter_thresholds_pick_fewer():
    hashes = [_hash(i % 5, i // 5) for i in range(20)]
    loose = pick_diverse(hashes, 27, 2, 4)
    strict = pick_diverse(hashes, 27, 10, 16)
    assert len(strict) <= len(loose)
    assert loose[0] == strict[0] == 0


def test_empty_and_single():
    assert pick_diverse([], 5, 5, 10) == []
    assert pick_diverse([_hash(3)], 5, 5, 10) == [0]


def test_hash_batch_is_small():
    # Guard against someone "optimising" this back to a whole-video read.
    assert HASH_BATCH <= 64
