from bci2000_bids.convert import discover_inputs


def test_deterministic_discovery(tmp_path):
    (tmp_path / "b.dat").write_bytes(b"x")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "a.dat").write_bytes(b"x")
    assert [path.name for path in discover_inputs(tmp_path)] == ["b.dat"]
    assert [path.name for path in discover_inputs(tmp_path, recursive=True)] == ["a.dat", "b.dat"]
