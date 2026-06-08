from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "lab.db"
TEACHER_SIGNUP_KEY = os.environ.get("TEACHER_SIGNUP_KEY", "teacher-invite-2026")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")
TEMP_STUDENT_USERNAME = os.environ.get("TEMP_STUDENT_USERNAME", "student01")
TEMP_STUDENT_PASSWORD = os.environ.get("TEMP_STUDENT_PASSWORD", "student1234")
TEMP_STUDENT_2_USERNAME = os.environ.get("TEMP_STUDENT_2_USERNAME", "student02")
TEMP_STUDENT_2_PASSWORD = os.environ.get("TEMP_STUDENT_2_PASSWORD", "student12345")

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
    "lab_start_time",
    "lab_end_time",
    "experiment_title",
    "purpose",
    "reagents",
    "safety_plan",
    "status",
    "created_at",
]

USER_FIELDS = [
    "id",
    "username",
    "name",
    "student_id",
    "role",
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                student_id TEXT DEFAULT '',
                role TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        admin = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (ADMIN_USERNAME,),
        ).fetchone()
        if admin is None:
            conn.execute(
                """
                INSERT INTO users
                    (username, password_hash, name, student_id, role, status)
                VALUES (?, ?, ?, '', 'admin', 'approved')
                """,
                (
                    ADMIN_USERNAME,
                    generate_password_hash(ADMIN_PASSWORD),
                    "최고 관리자",
                ),
            )

        temporary_students = [
            (TEMP_STUDENT_USERNAME, TEMP_STUDENT_PASSWORD, "임시 학생 1"),
            (TEMP_STUDENT_2_USERNAME, TEMP_STUDENT_2_PASSWORD, "임시 학생 2"),
        ]
        for username, password, name in temporary_students:
            temp_student = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            password_hash = generate_password_hash(password)
            if temp_student is None:
                conn.execute(
                    """
                    INSERT INTO users
                        (username, password_hash, name, student_id, role, status)
                    VALUES (?, ?, ?, ?, 'student', 'approved')
                    """,
                    (
                        username,
                        password_hash,
                        name,
                        username,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE users
                    SET password_hash = ?,
                        name = ?,
                        student_id = ?,
                        role = 'student',
                        status = 'approved'
                    WHERE username = ?
                    """,
                    (password_hash, name, username, username),
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
                lab_start_time TEXT DEFAULT '',
                lab_end_time TEXT DEFAULT '',
                experiment_title TEXT NOT NULL,
                purpose TEXT NOT NULL,
                reagents TEXT NOT NULL,
                safety_plan TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '대기',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        ensure_column(conn, "lab_requests", "owner_token", "TEXT DEFAULT ''")
        ensure_column(conn, "lab_requests", "user_id", "INTEGER DEFAULT NULL")
        ensure_column(conn, "lab_requests", "lab_start_time", "TEXT DEFAULT ''")
        ensure_column(conn, "lab_requests", "lab_end_time", "TEXT DEFAULT ''")
        conn.execute(
            """
            UPDATE lab_requests
            SET lab_start_time = lab_time
            WHERE (lab_start_time IS NULL OR lab_start_time = '')
              AND lab_time IS NOT NULL
              AND lab_time != ''
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
    if role() not in {"teacher", "admin"}:
        return jsonify({"message": "선생님 관리자 권한이 필요합니다."}), 403
    return None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/session")
def session_status():
    return jsonify(
        {
            "role": role(),
            "student": session.get("student"),
            "user": session.get("user"),
        }
    )


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    invite_key = data.get("invite_key", "")
    privacy_agreed = data.get("privacy_agreed") is True

    if not privacy_agreed:
        return jsonify({"message": "개인정보 수집 및 이용에 동의해야 합니다."}), 400
    if not username or not password or not name:
        return jsonify({"message": "아이디, 비밀번호, 이름은 필수입니다."}), 400
    if len(username) < 4:
        return jsonify({"message": "아이디는 4자 이상이어야 합니다."}), 400
    if len(password) < 8:
        return jsonify({"message": "비밀번호는 8자 이상이어야 합니다."}), 400
    if invite_key != TEACHER_SIGNUP_KEY:
        return jsonify({"message": "선생님 가입 초대키가 올바르지 않습니다."}), 401

    with get_db() as conn:
        duplicate = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if duplicate:
            return jsonify({"message": "이미 사용 중인 아이디입니다."}), 409

        conn.execute(
            """
            INSERT INTO users
                (username, password_hash, name, student_id, role, status)
            VALUES (?, ?, ?, '', 'teacher', 'pending')
            """,
            (
                username,
                generate_password_hash(password),
                name,
            ),
        )

    return jsonify({"message": "가입 신청이 완료되었습니다. 관리자 승인 후 로그인할 수 있습니다."}), 201


@app.post("/api/login")
def account_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    with get_db() as conn:
        user = conn.execute(
            """
            SELECT id, username, password_hash, name, student_id, role, status
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"message": "아이디 또는 비밀번호가 올바르지 않습니다."}), 401
    if user["status"] == "pending":
        return jsonify({"message": "가입 승인 대기 중입니다."}), 403
    if user["status"] == "rejected":
        return jsonify({"message": "가입이 승인되지 않은 계정입니다."}), 403
    if user["role"] not in {"student", "teacher", "admin"}:
        return jsonify({"message": "사용할 수 없는 계정입니다."}), 403

    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "name": user["name"],
        "student_id": user["student_id"],
        "role": user["role"],
    }
    if user["role"] == "student":
        session["student"] = {
            "name": user["name"],
            "student_id": user["student_id"],
        }

    return jsonify({"role": user["role"], "user": session["user"], "student": session.get("student")})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"role": None})


@app.get("/api/users")
def list_users():
    if role() != "admin":
        return jsonify({"message": "최고 관리자 권한이 필요합니다."}), 403

    fields = ", ".join(USER_FIELDS)
    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT {fields}
            FROM users
            WHERE role IN ('student', 'teacher', 'admin')
            ORDER BY role, status DESC, id DESC
            """
        ).fetchall()

    return jsonify([row_dict(row, USER_FIELDS) for row in rows])


@app.post("/api/users/students")
def create_student_user():
    if role() != "admin":
        return jsonify({"message": "최고 관리자 권한이 필요합니다."}), 403

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    student_id = data.get("student_id", "").strip()
    password = data.get("password", "")

    if not name or not student_id or not password:
        return jsonify({"message": "이름, 학번, 초기 비밀번호는 필수입니다."}), 400
    if len(password) < 8:
        return jsonify({"message": "초기 비밀번호는 8자 이상이어야 합니다."}), 400
    if len(name) > 30 or len(student_id) > 30:
        return jsonify({"message": "이름 또는 학번이 너무 깁니다."}), 400

    with get_db() as conn:
        duplicate = conn.execute(
            "SELECT id FROM users WHERE username = ? OR student_id = ?",
            (student_id, student_id),
        ).fetchone()
        if duplicate:
            return jsonify({"message": "이미 등록된 학번입니다."}), 409

        cursor = conn.execute(
            """
            INSERT INTO users
                (username, password_hash, name, student_id, role, status)
            VALUES (?, ?, ?, ?, 'student', 'approved')
            """,
            (
                student_id,
                generate_password_hash(password),
                name,
                student_id,
            ),
        )
        row = conn.execute(
            f"SELECT {', '.join(USER_FIELDS)} FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return jsonify(row_dict(row, USER_FIELDS)), 201


@app.patch("/api/users/<int:user_id>")
def update_user_status(user_id: int):
    if role() != "admin":
        return jsonify({"message": "최고 관리자 권한이 필요합니다."}), 403

    data = request.get_json(silent=True) or {}
    status = data.get("status", "").strip()
    if status not in {"pending", "approved", "rejected"}:
        return jsonify({"message": "회원 상태 값이 올바르지 않습니다."}), 400

    with get_db() as conn:
        target = conn.execute(
            "SELECT id, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if target is None:
            return jsonify({"message": "회원을 찾을 수 없습니다."}), 404
        if target["role"] == "admin":
            return jsonify({"message": "최고 관리자 상태는 변경할 수 없습니다."}), 400

        conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
        row = conn.execute(
            f"SELECT {', '.join(USER_FIELDS)} FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    return jsonify(row_dict(row, USER_FIELDS))


@app.delete("/api/users/<int:user_id>")
def delete_user(user_id: int):
    if role() != "admin":
        return jsonify({"message": "최고 관리자 권한이 필요합니다."}), 403

    with get_db() as conn:
        target = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        if target is None:
            return jsonify({"message": "회원을 찾을 수 없습니다."}), 404
        if target["role"] == "admin":
            return jsonify({"message": "최고 관리자 계정은 삭제할 수 없습니다."}), 400
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    return jsonify({"message": "회원 계정이 삭제되었습니다."})


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
    params: tuple[int, ...] = ()
    where = ""

    if role() == "student":
        where = "WHERE user_id = ?"
        params = (session["user_id"],)
    elif role() not in {"teacher", "admin"}:
        return jsonify({"message": "로그인이 필요합니다."}), 401

    with get_db() as conn:
        rows = conn.execute(f"SELECT {fields} FROM lab_requests {where} ORDER BY id DESC", params).fetchall()

    return jsonify([row_dict(row, REQUEST_FIELDS) for row in rows])


@app.post("/api/requests")
def create_request():
    if role() != "student":
        return jsonify({"message": "학생 로그인이 필요합니다."}), 403

    data = request.get_json(silent=True) or {}
    student = session.get("student") or {}
    start_time = data.get("lab_start_time", "").strip()
    end_time = data.get("lab_end_time", "").strip()
    if not valid_time_range(start_time, end_time):
        return jsonify({"message": "실험 종료 시간은 시작 시간보다 늦어야 합니다."}), 400

    values = {
        "user_id": session["user_id"],
        "student_name": student.get("name", "").strip(),
        "student_id": student.get("student_id", "").strip(),
        "lab_date": data.get("lab_date", "").strip(),
        "lab_time": start_time,
        "lab_start_time": start_time,
        "lab_end_time": end_time,
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
                (user_id, student_name, student_id, lab_date, lab_time, lab_start_time, lab_end_time, experiment_title, purpose, reagents, safety_plan)
            VALUES
                (:user_id, :student_name, :student_id, :lab_date, :lab_time, :lab_start_time, :lab_end_time, :experiment_title, :purpose, :reagents, :safety_plan)
            """,
            values,
        )
        row = conn.execute(
            f"SELECT {', '.join(REQUEST_FIELDS)} FROM lab_requests WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return jsonify(row_dict(row, REQUEST_FIELDS)), 201


@app.put("/api/requests/<int:request_id>")
def update_request(request_id: int):
    if role() != "student":
        return jsonify({"message": "학생 로그인이 필요합니다."}), 403

    data = request.get_json(silent=True) or {}
    student = session.get("student") or {}
    start_time = data.get("lab_start_time", "").strip()
    end_time = data.get("lab_end_time", "").strip()
    if not valid_time_range(start_time, end_time):
        return jsonify({"message": "실험 종료 시간은 시작 시간보다 늦어야 합니다."}), 400

    values = {
        "id": request_id,
        "user_id": session["user_id"],
        "student_name": student.get("name", "").strip(),
        "student_id": student.get("student_id", "").strip(),
        "lab_date": data.get("lab_date", "").strip(),
        "lab_time": start_time,
        "lab_start_time": start_time,
        "lab_end_time": end_time,
        "experiment_title": data.get("experiment_title", "").strip(),
        "purpose": data.get("purpose", "").strip(),
        "reagents": data.get("reagents", "").strip(),
        "safety_plan": data.get("safety_plan", "").strip(),
    }
    if any(not value for key, value in values.items() if key != "id"):
        return jsonify({"message": "모든 신청 항목을 작성해야 합니다."}), 400

    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE lab_requests
            SET student_name = :student_name,
                student_id = :student_id,
                lab_date = :lab_date,
                lab_time = :lab_time,
                lab_start_time = :lab_start_time,
                lab_end_time = :lab_end_time,
                experiment_title = :experiment_title,
                purpose = :purpose,
                reagents = :reagents,
                safety_plan = :safety_plan,
                status = '대기'
            WHERE id = :id AND user_id = :user_id
            """,
            values,
        )
        if cursor.rowcount == 0:
            return jsonify({"message": "수정할 수 있는 신청서를 찾지 못했습니다."}), 404
        row = conn.execute(
            f"SELECT {', '.join(REQUEST_FIELDS)} FROM lab_requests WHERE id = ?",
            (request_id,),
        ).fetchone()

    return jsonify(row_dict(row, REQUEST_FIELDS))


def valid_time_range(start_time: str, end_time: str) -> bool:
    try:
        start_hour, start_minute = (int(value) for value in start_time.split(":"))
        end_hour, end_minute = (int(value) for value in end_time.split(":"))
    except (TypeError, ValueError):
        return False

    if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
        return False
    if not (0 <= start_minute <= 59 and 0 <= end_minute <= 59):
        return False
    return end_hour * 60 + end_minute > start_hour * 60 + start_minute


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
