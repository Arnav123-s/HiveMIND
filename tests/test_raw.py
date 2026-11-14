from training import raw


def test_the_hive_reads_what_it_does_not_know_yet_but_can_learn():
    scored = [(float(i), f"piece{i}") for i in range(10)]   # error 0 (known) .. 9 (noise)
    kept = raw.pick(scored, 3)
    assert kept == ["piece8", "piece7", "piece6"]             # the hardest of the middle band; 9 is left as noise
    assert "piece0" not in raw.pick(scored, 10) and "piece9" not in raw.pick(scored, 10)


def test_each_organ_reads_from_its_nearest_sources():
    assert max(raw.BY_ORGAN["code"], key=raw.BY_ORGAN["code"].get) == "code"
    assert "code" not in raw.BY_ORGAN["words"]
    assert set(raw.SOURCES) >= {w for weights in raw.BY_ORGAN.values() for w in weights}


def test_answers_are_kept_as_text_with_code_blocks_and_no_markup():
    t = raw._text("<p>Use <code>x = 1</code> &amp; then:</p><pre><code>print(x)\n</code></pre><p>Done.</p>")
    assert "<" not in t and "&amp;" not in t and "x = 1 & then" in t and "```\nprint(x)" in t
