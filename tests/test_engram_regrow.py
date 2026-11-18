import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("torch")

from training.experiments import engram_regrow as codec
from gguf import GGUFReader, GGUFWriter


def adapter(path, name, data):
    writer = GGUFWriter(path, "qwen3")
    writer.add_type("adapter")
    writer.add_name(name)
    writer.add_string("adapter.type", "lora")
    writer.add_float32("adapter.lora.alpha", 8.)
    writer.add_tensor("layer.lora_a", data.astype("float16"))
    writer.add_tensor("layer.lora_b", np.ones((3, 5), dtype="float16"))
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()


@pytest.mark.parametrize("mode", ["exact", "absmean", "fit", "groupfit"])
def test_regrow_reads_only_the_capsule_and_correct_ancestors(tmp_path, mode):
    parent, child, base, capsule, result = (tmp_path / n for n in ("p", "c", "b", "patch", "new"))
    base.write_bytes(b"shared base")
    data = np.zeros((3, 5), dtype="float16")
    adapter(parent, "A", data)
    data[2, :3] = [0.15, -0.07, 0.2]
    adapter(child, "BC", data)
    hashes = {k: codec.digest(path) for k, path in (("parent", parent), ("base", base), ("child", child))}
    stats = codec.encode(parent, child, capsule, mode, hashes)
    assert stats["changed_tensors"] == 1
    child.unlink()
    codec.restore(parent, base, capsule, result)
    if mode == "exact":
        assert codec.digest(result) == hashes["child"]
    else:
        tensors = {t.name: t.data for t in GGUFReader(result).tensors}
        assert np.array_equal(tensors["layer.lora_a"][:2], data[:2])
        assert bool(np.isfinite(tensors["layer.lora_a"]).all())
        assert np.array_equal(tensors["layer.lora_b"], np.ones((3, 5)))
    good = result.read_bytes()
    for wrong_parent, wrong_base in ((base, base), (parent, parent)):
        with pytest.raises(ValueError, match="fingerprint mismatch"):
            codec.restore(wrong_parent, wrong_base, capsule, result)
        assert result.read_bytes() == good


def test_three_valued_code_preserves_zero_odd_length_groups():
    for mode in ("absmean", "fit", "groupfit"):
        parent = np.zeros((3, 5), dtype=np.float16)
        width, data = codec.ternarize(parent.astype(np.float32), mode)
        assert np.array_equal(codec.decode(parent, data, mode, width), parent)
