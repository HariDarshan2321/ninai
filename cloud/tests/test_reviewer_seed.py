from ninai_cloud.reviewer_seed import SAMPLES


def test_reviewer_fixture_is_synthetic_and_source_backed() -> None:
    assert len(SAMPLES) == 3
    assert {sample.memory_type for sample in SAMPLES} == {"decision", "constraint", "procedure"}
    assert all(sample.source_uri.startswith("reviewer://atlas/") for sample in SAMPLES)
    joined = " ".join(sample.content.lower() for sample in SAMPLES)
    assert "synthetic" in joined
    assert "credentials" in joined
