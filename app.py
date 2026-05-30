from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "lab.db"
TEACHER_KEY = os.environ.get("TEACHER_KEY", "teacher1234")
STUDENT_PASSWORD = os.environ.get("STUDENT_PASSWORD", "student1234")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-before-deploy")

REAGENT_FIELDS = [
    "id",
    "name",
    "english_name",
    "chemical_code",
    "hazard_level",
    "risk_notes",
    "quantity",
    "location",
    "purchase_date",
    "recommended_months",
    "manager",
    "created_at",
]

REQUEST_FIELDS = [
    "id",
    "student_name",
    "student_id",
    "lab_date",
    "lab_time",
    "experiment_title",
    "purpose",
    "reagents",
    "safety_plan",
    "status",
    "created_at",
]


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reagents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                quantity TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        ensure_column(conn, "reagents", "english_name", "TEXT DEFAULT ''")
        ensure_column(conn, "reagents", "chemical_code", "TEXT DEFAULT ''")
        ensure_column(conn, "reagents", "hazard_level", "TEXT DEFAULT ''")
        ensure_column(conn, "reagents", "risk_notes", "TEXT DEFAULT ''")
        ensure_column(conn, "reagents", "purchase_date", "TEXT DEFAULT ''")
        ensure_column(conn, "reagents", "recommended_months", "INTEGER DEFAULT NULL")
        ensure_column(conn, "reagents", "manager", "TEXT DEFAULT ''")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lab_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                student_id TEXT NOT NULL,
                lab_date TEXT NOT NULL,
                lab_time TEXT NOT NULL,
                experiment_title TEXT NOT NULL,
                purpose TEXT NOT NULL,
                reagents TEXT NOT NULL,
                safety_plan TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '대기',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        count = conn.execute("SELECT COUNT(*) FROM reagents").fetchone()[0]
        if count == 0:
            conn.executemany(
                """
                INSERT INTO reagents
                    (name, english_name, chemical_code, hazard_level, risk_notes, quantity, location, purchase_date, recommended_months, manager)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ("염산", "Hydrochloric acid", "HCl", "위험", "부식성. 염기성 물질과 분리 보관", "450 mL", "A-1", "2026-03-01", None, "과학부"),
                    ("에탄올", "Ethanol", "C2H5OH", "높음", "인화성. 화기 근처 보관 금지", "700 mL", "B-2", "2026-05-10", 12, "화학실"),
                    ("수산화나트륨", "Sodium hydroxide", "NaOH", "위험", "강한 염기성. 피부와 눈 접촉 주의", "120 g", "C-1", "2026-01-12", None, "과학부"),
                    ("과산화수소", "Hydrogen peroxide", "H2O2", "높음", "산화성. 환원제와 분리 보관", "300 mL", "D-1", "2026-04-20", 12, "화학실"),
                ],
            )

        request_count = conn.execute("SELECT COUNT(*) FROM lab_requests").fetchone()[0]
        if request_count == 0:
            conn.execute(
                """
                INSERT INTO lab_requests
                    (student_name, student_id, lab_date, lab_time, experiment_title, purpose, reagents, safety_plan)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "김하늘",
                    "30201",
                    "2026-06-05",
                    "15:30",
                    "산염기 중화 반응 관찰",
                    "염산과 수산화나트륨의 중화 반응을 관찰하고 pH 변화를 확인한다.",
                    "염산, 수산화나트륨, 페놀프탈레인",
                    "보안경과 장갑을 착용하고 산과 염기를 분리하여 취급한다.",
                ),
            )


def row_dict(row: sqlite3.Row, fields: list[str]) -> dict:
    return {field: row[field] for field in fields}


def role() -> str | None:
    return session.get("role")


def require_teacher():
    if role() != "teacher":
        return jsonify({"message": "선생님 관리자 권한이 필요합니다."}), 403
    return None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/session")
def session_status():
    return jsonify({"role": role(), "student": session.get("student")})


@app.post("/api/login/student")
def student_login():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    student_id = data.get("student_id", "").strip()
    password = data.get("password", "")

    if not name or not student_id:
        return jsonify({"message": "이름과 학번을 입력해야 합니다."}), 400
    if password != STUDENT_PASSWORD:
        return jsonify({"message": "학생 비밀번호가 올바르지 않습니다."}), 401

    session["role"] = "student"
    session["student"] = {"name": name, "student_id": student_id}
    return jsonify({"role": "student", "student": session["student"]})


@app.post("/api/login/teacher")
def teacher_login():
    data = request.get_json(silent=True) or {}
    if data.get("teacher_key") != TEACHER_KEY:
        return jsonify({"message": "교사 관리자 비밀번호가 올바르지 않습니다."}), 401

    session["role"] = "teacher"
    session.pop("student", None)
    return jsonify({"role": "teacher"})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"role": None})


@app.get("/api/reagents")
def list_reagents():
    keyword = request.args.get("q", "").strip()
    fields = ", ".join(REAGENT_FIELDS)

    with get_db() as conn:
        if keyword:
            like = f"%{keyword}%"
            rows = conn.execute(
                f"""
                SELECT {fields}
                FROM reagents
                WHERE name LIKE ?
                   OR english_name LIKE ?
                   OR chemical_code LIKE ?
                   OR hazard_level LIKE ?
                   OR risk_notes LIKE ?
                   OR quantity LIKE ?
                   OR location LIKE ?
                   OR purchase_date LIKE ?
                   OR manager LIKE ?
                ORDER BY id DESC
                """,
                (like, like, like, like, like, like, like, like, like),
            ).fetchall()
        else:
            rows = conn.execute(f"SELECT {fields} FROM reagents ORDER BY id DESC").fetchall()

    return jsonify([row_dict(row, REAGENT_FIELDS) for row in rows])


@app.post("/api/reagents")
def create_reagent():
    blocked = require_teacher()
    if blocked:
        return blocked

    values = normalize_reagent_payload(request.get_json(silent=True) or {})
    if not values["name"] or not values["location"]:
        return jsonify({"message": "시약명과 보관 위치는 필수입니다."}), 400

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reagents
                (name, english_name, chemical_code, hazard_level, risk_notes, quantity, location, purchase_date, recommended_months, manager)
            VALUES
                (:name, :english_name, :chemical_code, :hazard_level, :risk_notes, :quantity, :location, :purchase_date, :recommended_months, :manager)
            """,
            values,
        )
        row = conn.execute(
            f"SELECT {', '.join(REAGENT_FIELDS)} FROM reagents WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return jsonify(row_dict(row, REAGENT_FIELDS)), 201


@app.put("/api/reagents/<int:reagent_id>")
def update_reagent(reagent_id: int):
    blocked = require_teacher()
    if blocked:
        return blocked

    values = normalize_reagent_payload(request.get_json(silent=True) or {})
    values["id"] = reagent_id
    if not values["name"] or not values["location"]:
        return jsonify({"message": "시약명과 보관 위치는 필수입니다."}), 400

    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE reagents
            SET name = :name,
                english_name = :english_name,
                chemical_code = :chemical_code,
                hazard_level = :hazard_level,
                risk_notes = :risk_notes,
                quantity = :quantity,
                location = :location,
                purchase_date = :purchase_date,
                recommended_months = :recommended_months,
                manager = :manager
            WHERE id = :id
            """,
            values,
        )
        if cursor.rowcount == 0:
            return jsonify({"message": "해당 시약을 찾을 수 없습니다."}), 404
        row = conn.execute(
            f"SELECT {', '.join(REAGENT_FIELDS)} FROM reagents WHERE id = ?",
            (reagent_id,),
        ).fetchone()

    return jsonify(row_dict(row, REAGENT_FIELDS))


@app.delete("/api/reagents/<int:reagent_id>")
def delete_reagent(reagent_id: int):
    blocked = require_teacher()
    if blocked:
        return blocked

    with get_db() as conn:
        cursor = conn.execute("DELETE FROM reagents WHERE id = ?", (reagent_id,))

    if cursor.rowcount == 0:
        return jsonify({"message": "해당 시약을 찾을 수 없습니다."}), 404

    return jsonify({"message": "삭제되었습니다."})


@app.get("/api/requests")
def list_requests():
    fields = ", ".join(REQUEST_FIELDS)
    params: tuple[str, ...] = ()
    where = ""

    if role() == "student":
        student = session.get("student") or {}
        where = "WHERE student_id = ?"
        params = (student.get("student_id", ""),)

    with get_db() as conn:
        rows = conn.execute(f"SELECT {fields} FROM lab_requests {where} ORDER BY id DESC", params).fetchall()

    return jsonify([row_dict(row, REQUEST_FIELDS) for row in rows])


@app.post("/api/requests")
def create_request():
    if role() != "student":
        return jsonify({"message": "학생 로그인 후 신청할 수 있습니다."}), 403

    data = request.get_json(silent=True) or {}
    student = session.get("student") or {}
    values = {
        "student_name": student.get("name", ""),
        "student_id": student.get("student_id", ""),
        "lab_date": data.get("lab_date", "").strip(),
        "lab_time": data.get("lab_time", "").strip(),
        "experiment_title": data.get("experiment_title", "").strip(),
        "purpose": data.get("purpose", "").strip(),
        "reagents": data.get("reagents", "").strip(),
        "safety_plan": data.get("safety_plan", "").strip(),
    }

    if any(not value for value in values.values()):
        return jsonify({"message": "모든 신청 항목을 작성해야 합니다."}), 400

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO lab_requests
                (student_name, student_id, lab_date, lab_time, experiment_title, purpose, reagents, safety_plan)
            VALUES
                (:student_name, :student_id, :lab_date, :lab_time, :experiment_title, :purpose, :reagents, :safety_plan)
            """,
            values,
        )
        row = conn.execute(
            f"SELECT {', '.join(REQUEST_FIELDS)} FROM lab_requests WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return jsonify(row_dict(row, REQUEST_FIELDS)), 201


@app.patch("/api/requests/<int:request_id>")
def update_request_status(request_id: int):
    blocked = require_teacher()
    if blocked:
        return blocked

    status = (request.get_json(silent=True) or {}).get("status", "").strip()
    if status not in {"대기", "승인", "반려"}:
        return jsonify({"message": "상태 값이 올바르지 않습니다."}), 400

    with get_db() as conn:
        cursor = conn.execute("UPDATE lab_requests SET status = ? WHERE id = ?", (status, request_id))
        if cursor.rowcount == 0:
            return jsonify({"message": "해당 신청서를 찾을 수 없습니다."}), 404
        row = conn.execute(
            f"SELECT {', '.join(REQUEST_FIELDS)} FROM lab_requests WHERE id = ?",
            (request_id,),
        ).fetchone()

    return jsonify(row_dict(row, REQUEST_FIELDS))


def normalize_reagent_payload(data: dict) -> dict:
    months = data.get("recommended_months")
    try:
        months_value = int(months) if str(months).strip() else None
    except (TypeError, ValueError):
        months_value = None

    return {
        "name": data.get("name", "").strip(),
        "english_name": data.get("english_name", "").strip(),
        "chemical_code": data.get("chemical_code", "").strip(),
        "hazard_level": data.get("hazard_level", "").strip(),
        "risk_notes": data.get("risk_notes", "").strip(),
        "quantity": data.get("quantity", "").strip(),
        "location": data.get("location", "").strip(),
        "purchase_date": data.get("purchase_date", "").strip(),
        "recommended_months": months_value,
        "manager": data.get("manager", "").strip() or "미지정",
    }


init_db()


if __name__ == "__main__":
    app.run(debug=True)
