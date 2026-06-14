from api.logic import recommander_action

def test_action_a_risque():
    a_risque, action = recommander_action(0.9)
    assert a_risque is True
    assert "pause" in action.lower()

def test_action_fidele():
    a_risque, action = recommander_action(0.1)
    assert a_risque is False
    assert "fidele" in action.lower()