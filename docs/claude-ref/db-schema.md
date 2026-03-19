# DB 스키마 참고

> DB: PostgreSQL 17 — `localhost:5432/aipass` (postgres/1234)

## member 테이블

```sql
CREATE TABLE member (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR UNIQUE NOT NULL,
    password    VARCHAR NOT NULL,          -- BCrypt 해시
    name        VARCHAR NOT NULL,
    email       VARCHAR NOT NULL,
    phone       VARCHAR,
    role        VARCHAR DEFAULT 'ADMIN',
    created_at  TIMESTAMP DEFAULT NOW()
);
```

## MyBatis Mapper 위치
- 인터페이스: `AIpassBackend/src/main/java/com/aipass/dao/MemberMapper.java`
- SQL XML: `AIpassBackend/src/main/resources/sqls/member.xml`

### MemberMapper 메서드 목록
| 메서드 | 설명 |
|--------|------|
| `findByUsername(String)` | 로그인용 단건 조회 |
| `insertMember(MemberDTO)` | 회원가입 |
| `countByUsername(String)` | 중복 ID 체크 |
| `findByNameAndEmail(name, email)` | ID 찾기 |
| `findByUsernameAndEmail(username, email)` | 비밀번호 재설정 인증 |
| `updatePassword(username, password)` | 비밀번호 변경 |
| `updateMember(MemberDTO)` | 프로필 수정 (name, email, phone) |
