"""The page as a viewer gets it: Streamlit's AppTest runs app.py headless. The default question replays a saved model
reply (D30), so these run offline."""
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "app.py")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")  # never reach the network from a test
    return AppTest.from_file(APP, default_timeout=60)


def html(at):
    return "".join(e.proto.body for e in at.get("html"))


def test_analyst_sees_the_garden_by_day_with_no_prototype_switcher(app):
    page = html(app.run())
    assert not app.exception
    assert 'id="garden-cfg" data-mode="day"' in page
    assert "variant" not in page and "proto-bar" not in page


def test_merchant_manager_sees_the_garden_by_night(app):
    app.run()
    app.text_input[0].set_value("")  # no question: only the role matters here
    app.selectbox[0].set_value("Merchant manager").run()
    assert not app.exception
    assert 'data-mode="night"' in html(app)


def test_exhibit_a_walks_from_week_5_to_week_6_and_fades_noise(app):
    page = html(app.run())
    bridge = re.findall(r'<div class="ln w">(.*?)</div>', page)
    names = [re.sub("<.*?>", "", b.split("</span>")[0]) for b in bridge]
    assert names[0] == "Week 5 Success rate" and names[1] == "Mix effect" and names[-1] == "Week 6 Success rate"
    assert "92.66%" in bridge[0] and "88.66%" in bridge[-1]
    assert "wb down" in bridge[1]  # the Mix effect carries the drop
    assert all("noise" in b for b in bridge[2:-1])  # every rate effect sits inside its 95% interval


def test_page_writes_words_out_in_full(app):
    page = re.sub(r"<pre.*?</pre>", "", html(app.run()), flags=re.S)  # the SQL keeps its own names
    text = re.sub("<.*?>", " ", page)
    assert not re.search(r"\bwk\d|\dpp\b", text)


def test_demo_question_with_an_edited_window_still_answers_offline(app):
    app.run()
    app.text_input[0].set_value("How's success rate lately?").run()
    app.session_state.weeks = [5, 6]  # what the Window chip's Re-run stores
    page = html(app.run())
    assert not app.exception
    assert "Model unavailable" not in page and "headline by the pipeline" in page
    assert "92.66%" in page and "88.66%" in page


def test_garden_celebrates_an_answer_and_storms_on_a_rejection_only(app):
    assert html(app.run()).count('data-garden="celebrate"') == 1
    app.text_input[0].set_value("Show me settlements")
    app.selectbox[0].set_value("Merchant manager").run()
    assert 'data-garden="storm"' in html(app) and 'data-garden="celebrate"' not in html(app)
    app.text_input[0].set_value("What is the weather in Mumbai?").run()  # no key: Model unavailable
    assert "Model unavailable" in html(app) and "data-garden" not in html(app)
