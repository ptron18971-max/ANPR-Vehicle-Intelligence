"""Tests for IdentityFusionEngine -- the real weighted multi-modal fusion math.

Previously this logic was only exercised via `tests/evaluate_fusion.py`, which
has no `test_`-prefixed function and so was never collected/run by pytest
(Issue #7). `tests/test_pipeline.py` mocks `fusion_engine.fuse()` entirely, so
it doesn't cover this module either. These tests close that gap.
"""

import pytest

from vehicle_reid.fusion import IdentityFusionEngine


def _search_result(similarity_score, vehicle_id="VEH_1001", plate_text="KA01AB1234",
                    vehicle_type="sedan", vehicle_color="white", vector_id=7,
                    camera_id="c_00", timestamp="2026-04-10T09:58:00Z"):
    return {
        "vector_id": vector_id,
        "similarity_score": similarity_score,
        "metadata": {
            "vehicle_id": vehicle_id,
            "camera_id": camera_id,
            "timestamp": timestamp,
            "plate_text": plate_text,
            "vehicle_type": vehicle_type,
            "vehicle_color": vehicle_color,
        },
    }


def _observation(plate_text="KA01AB1234", vehicle_type="sedan", vehicle_color="white"):
    return {"plate_text": plate_text, "vehicle_type": vehicle_type, "vehicle_color": vehicle_color}


class TestFuseWeightedAverage:
    def test_perfect_match_across_all_modalities(self):
        engine = IdentityFusionEngine(appearance_weight=0.5, ocr_weight=0.3, attribute_weight=0.2)
        result = engine.fuse(_search_result(similarity_score=1.0), _observation())

        # appearance_score = (1.0 + 1.0) / 2 = 1.0; ocr_score = 1.0 (exact plate);
        # attribute_score = 1.0 (type & color both match)
        # final = 0.5*1.0 + 0.3*1.0 + 0.2*1.0 = 1.0
        assert result["identity_confidence"] == pytest.approx(1.0)
        assert result["appearance_confidence"] == pytest.approx(1.0)
        assert result["vehicle_id"] == "VEH_1001"
        assert result["supporting_evidence"]["match_strategy"] == "multimodal_fusion"

    def test_weighted_average_matches_manual_calculation(self):
        """Cosine similarity 0.6, plate completely different, one attribute matches."""
        engine = IdentityFusionEngine(appearance_weight=0.5, ocr_weight=0.3, attribute_weight=0.2)
        result = engine.fuse(
            _search_result(similarity_score=0.6, plate_text="MH12ZZ9999", vehicle_color="black"),
            _observation(vehicle_color="white"),  # color mismatch, type still matches
        )

        appearance_score = (0.6 + 1.0) / 2.0  # 0.8
        ocr_score = engine._calculate_ocr_match("KA01AB1234", "MH12ZZ9999")
        attribute_score = 0.5  # type matches, color doesn't -> 1/2

        expected = 0.5 * appearance_score + 0.3 * ocr_score + 0.2 * attribute_score
        assert result["identity_confidence"] == pytest.approx(round(expected, 4))
        assert result["supporting_evidence"]["attribute_match_score"] == pytest.approx(0.5)

    def test_appearance_similarity_is_remapped_from_cosine_range(self):
        """similarity_score of -1.0 (maximally dissimilar cosine) should map to 0.0, not go negative."""
        engine = IdentityFusionEngine()
        result = engine.fuse(_search_result(similarity_score=-1.0), _observation())
        assert result["appearance_confidence"] == pytest.approx(0.0)

    def test_missing_plate_and_attributes_fall_back_to_neutral_scores(self):
        engine = IdentityFusionEngine()
        search_result = _search_result(similarity_score=1.0, plate_text=None,
                                        vehicle_type=None, vehicle_color=None)
        observation = _observation(plate_text=None, vehicle_type=None, vehicle_color=None)
        result = engine.fuse(search_result, observation)

        assert result["supporting_evidence"]["plate_match_score"] == pytest.approx(0.5)
        assert result["supporting_evidence"]["attribute_match_score"] == pytest.approx(0.5)

    def test_weights_are_configurable_and_still_sum_correctly(self):
        engine = IdentityFusionEngine(appearance_weight=1.0, ocr_weight=0.0, attribute_weight=0.0)
        # Even with a totally different plate/attributes, appearance-only weighting
        # should make identity_confidence track appearance_confidence exactly.
        result = engine.fuse(
            _search_result(similarity_score=0.4, plate_text="ZZ00ZZ0000", vehicle_type="truck"),
            _observation(plate_text="KA01AB1234", vehicle_type="sedan"),
        )
        assert result["identity_confidence"] == pytest.approx(result["appearance_confidence"])


class TestOcrMatching:
    """Regression coverage for Issue #8: substitution-aware, partial-read-aware
    plate matching (previously generic difflib with no domain awareness)."""

    def setup_method(self):
        self.engine = IdentityFusionEngine()

    def test_exact_match(self):
        assert self.engine._calculate_ocr_match("KA01AB1234", "KA01AB1234") == 1.0

    @pytest.mark.parametrize("query,candidate", [
        ("KA01AB1234", "KAO1AB1234"),  # O <-> 0
        ("KA01AB1234", "KA0IAB1234"),  # I <-> 1
        ("KAS1AB1234", "KA51AB1234"),  # S <-> 5
        ("MH12BB1234", "MH12881234"),  # B <-> 8
        ("MH1ZZZ1234", "MH1222" + "1234"),  # Z <-> 2
    ])
    def test_common_ocr_substitutions_score_as_exact_match(self, query, candidate):
        assert self.engine._calculate_ocr_match(query, candidate) == pytest.approx(1.0)

    def test_partial_read_missing_trailing_character_scores_highly(self):
        """A plate read that's missing its last digit (e.g. occlusion/glare)
        should still score as a strong match via partial_ratio, not be penalized
        as heavily as an unrelated plate."""
        score = self.engine._calculate_ocr_match("KA01AB1234", "KA01AB123")
        assert score == pytest.approx(1.0)

    def test_punctuation_and_whitespace_are_ignored(self):
        assert self.engine._calculate_ocr_match("KA-01-AB-1234", "KA01AB1234") == pytest.approx(1.0)
        assert self.engine._calculate_ocr_match(" ka01ab1234 ", "KA01AB1234") == pytest.approx(1.0)

    def test_genuinely_different_plates_score_low(self):
        score = self.engine._calculate_ocr_match("KA01AB1234", "MH12ZZ9999")
        assert score < 0.5

    def test_missing_plate_returns_neutral_default(self):
        assert self.engine._calculate_ocr_match(None, "KA01AB1234") == 0.5
        assert self.engine._calculate_ocr_match("KA01AB1234", None) == 0.5
        assert self.engine._calculate_ocr_match(None, None) == 0.5

    def test_blank_string_plate_returns_neutral_default(self):
        assert self.engine._calculate_ocr_match("", "KA01AB1234") == 0.5
        assert self.engine._calculate_ocr_match("KA01AB1234", "   ") == 0.5


class TestAttributeMatching:
    def setup_method(self):
        self.engine = IdentityFusionEngine()

    def test_both_attributes_match(self):
        score = self.engine._calculate_attribute_match("sedan", "white", "sedan", "white")
        assert score == 1.0

    def test_one_attribute_matches(self):
        score = self.engine._calculate_attribute_match("sedan", "white", "sedan", "black")
        assert score == pytest.approx(0.5)

    def test_case_and_whitespace_insensitive(self):
        score = self.engine._calculate_attribute_match(" Sedan ", "WHITE", "sedan", "white")
        assert score == 1.0

    def test_no_comparable_attributes_returns_neutral_default(self):
        score = self.engine._calculate_attribute_match(None, None, "sedan", "white")
        assert score == 0.5
