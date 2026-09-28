import os
import sys
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.core_service.main import app, TEACHER_USER, TEACHER_PASSWORD


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health_endpoints(client):
    # 1. Basic health
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "core_service"

    # 2. Full health with metrics and uptime
    full_resp = client.get("/health/full")
    assert full_resp.status_code == 200
    full_data = full_resp.json()
    assert full_data["status"] == "healthy"
    assert "uptime_seconds" in full_data
    assert isinstance(full_data["uptime_seconds"], (int, float))
    assert "components" in full_data
    assert "metrics" in full_data
    assert "rag_metrics" in full_data
    assert "llm_metrics" in full_data
    assert "last_errors" in full_data
    assert full_data["components"]["kafka"] == "ready"


def test_student_portal_renders(client):
    resp = client.get("/student")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    html = resp.text

    # Check required UX elements from Block 2
    assert "Твой Путь" in html
    assert "Кабинет Ученика" in html
    assert "themeToggle" in html  # Light/Dark mode toggle
    assert "typing-indicator" in html  # Typing animation
    assert "uploadProgressWrap" in html  # Progress bar for textbook upload
    assert "btn-clear-chat" in html  # Clear history button
    assert "Быстрые вопросы" in html  # Quick chips
    assert "Квадратные уравнения" in html
    assert "Закон Ома" in html
    assert "Теорема Пифагора" in html


def test_teacher_dashboard_auth_and_analytics(client):
    # 1. Unauthorized without credentials
    unauth_resp = client.get("/teacher")
    assert unauth_resp.status_code == 401

    # 2. Unauthorized with wrong password
    bad_auth_resp = client.get("/teacher", auth=("wrong_user", "wrong_pass"))
    assert bad_auth_resp.status_code == 401

    # 3. Authorized access with TEACHER_USER and TEACHER_PASSWORD
    auth = (TEACHER_USER, TEACHER_PASSWORD)
    resp = client.get("/teacher", auth=auth)
    assert resp.status_code == 200
    html = resp.text

    # Check dashboard elements
    assert "Панель Учителя" in html
    assert "Динамика запросов за неделю" in html
    assert "<svg" in html  # Native SVG activity chart
    assert "Топ увлечений учеников" in html  # Top-5 hobbies
    assert "Тепловая карта успеваемости" in html  # Heatmap of lagging topics
    assert "Топ-5 тем по частоте запросов" in html  # Top-5 topics
    assert "students_progress.csv" in html  # CSV export link
    assert "timer" in html  # 30s auto-refresh timer


def test_teacher_csv_export(client):
    auth = (TEACHER_USER, TEACHER_PASSWORD)
    resp = client.get("/api/teacher/export_csv", auth=auth)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers.get("content-disposition", "")

    csv_text = resp.content.decode("utf-8-sig")
    assert "ID Ученика (MAX)" in csv_text
    assert "Интерес (Метафора)" in csv_text
    assert "Процент успеха" in csv_text


def test_textbooks_api(client):
    # 1. List textbooks
    resp = client.get("/api/student/textbooks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert isinstance(data["textbooks"], list)

    # 2. Reindex non-existent textbook
    reindex_resp = client.post("/api/student/textbook/reindex", json={"subject": "non_existent_subject_xyz"})
    assert reindex_resp.status_code == 200
    reindex_data = reindex_resp.json()
    # It gracefully handles missing files
    assert "status" in reindex_data

    # 3. Delete non-existent textbook
    del_resp = client.post("/api/student/textbook/delete", json={"subject": "temp_delete_test"})
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["status"] == "ok"


def test_student_ask_generation(client):
    resp = client.post("/api/student/ask", json={
        "user_id": "test_student_123",
        "topic": "Квадратные уравнения",
        "interest": "Футбол",
        "grade": 7
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert len(data["explanation"]) > 50
    assert "latency_ms" in data
    assert "source" in data
    assert data["quiz"] is not None
    assert len(data["quiz"]["options"]) >= 3
