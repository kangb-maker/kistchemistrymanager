# 배포 방법

## Render 기준

1. GitHub에 이 프로젝트 폴더를 업로드합니다.
2. Render에서 `New` -> `Web Service`를 선택합니다.
3. GitHub 저장소를 연결합니다.
4. 설정값을 아래처럼 둡니다.

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

5. 환경변수를 설정합니다.

```text
SECRET_KEY: 아무 긴 랜덤 문자열
TEACHER_KEY: 선생님 관리자 비밀번호
STUDENT_PASSWORD: 학생 공통 비밀번호
TEACHER_SIGNUP_KEY: 선생님 회원가입 초대키
ADMIN_USERNAME: 최고 관리자 아이디
ADMIN_PASSWORD: 최고 관리자 비밀번호
```

6. 배포가 끝나면 Render가 제공하는 `https://...onrender.com` 주소로 접속합니다.

## 주의

현재 DB는 SQLite(`lab.db`)입니다. 발표용/프로토타입에는 충분하지만, 실제 운영에서는 PostgreSQL로 바꾸는 것이 안전합니다.
