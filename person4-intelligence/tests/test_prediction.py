from prediction.route_predictor import predict_next, predict_path
from prediction.markov_predictor import build_transition_model, predict_next as markov_predict_next


def test_predict_next_ranks_by_probability(graph):
    result = predict_next(graph, "A")
    assert result == [("B", 0.8)]


def test_predict_next_empty_at_leaf(graph):
    assert predict_next(graph, "C") == []


def test_predict_path_beam_search(graph):
    paths = predict_path(graph, "A", hops=2, beam_width=2)
    assert paths[0][0] == ("A", "B", "C")
    assert paths[0][1] == round(0.8 * 0.1, 4)


def test_markov_predictor_learns_from_trajectories(normal_trajectory):
    model = build_transition_model([normal_trajectory])
    assert markov_predict_next(model, "A") == [("B", 1.0)]


def test_markov_predictor_empty_for_unseen_camera():
    model = build_transition_model([])
    assert markov_predict_next(model, "Z") == []
