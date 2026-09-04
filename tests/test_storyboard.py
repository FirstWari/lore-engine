from PIL import Image

from lore_engine.storyboard import compile_storyboard_sheets


def _frames(tmp_path, n):
    frames = []
    for i in range(n):
        p = tmp_path / f"frame_{i:02d}.jpg"
        Image.new("RGB", (64, 36), (i * 9 % 255, 80, 120)).save(p, "JPEG")
        frames.append({"timestamp": f"00:00:{i:02d}", "image_path": str(p)})
    return frames


def test_nine_frames_per_sheet(tmp_path):
    sheets = compile_storyboard_sheets(
        _frames(tmp_path, 11), output_dir=tmp_path / "out", cell_w=64, cell_h=36
    )
    assert [s["frame_count"] for s in sheets] == [9, 2]
    assert sheets[0]["start_time"] == "00:00:00" and sheets[0]["end_time"] == "00:00:08"
    assert sheets[1]["page"] == 2 and sheets[1]["total_pages"] == 2

    with Image.open(sheets[0]["image_path"]) as img:
        # 3 columns x 64 px + 4 paddings of 16 px
        assert img.size == (3 * 64 + 4 * 16, 3 * 36 + 4 * 16)
    with Image.open(sheets[1]["image_path"]) as img:
        assert img.size == (2 * 64 + 3 * 16, 36 + 2 * 16)


def test_empty_input_makes_no_sheet(tmp_path):
    assert compile_storyboard_sheets([], output_dir=tmp_path) == []
