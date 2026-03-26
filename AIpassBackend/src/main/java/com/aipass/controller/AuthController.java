package com.aipass.controller;

import com.aipass.dto.LoginRequest;
import com.aipass.dto.LoginResponse;
import com.aipass.dto.MemberDTO;
import com.aipass.dto.SignupRequest;
import com.aipass.service.EmailService;
import com.aipass.service.MemberService;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private static final String EMAIL_REGEX = "^[^\\s@]+@[^\\s@]+\\.[^\\s@]{2,}$";

    private final MemberService memberService;
    private final EmailService emailService;

    public AuthController(MemberService memberService, EmailService emailService) {
        this.memberService = memberService;
        this.emailService = emailService;
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest request, HttpSession session) {
        if (request.getUsername() == null || request.getPassword() == null) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "아이디와 비밀번호를 입력하세요."));
        }

        MemberDTO member = memberService.findByLoginId(request.getUsername());
        if (member == null || !memberService.checkPassword(request.getPassword(), member.getPassword())) {
            return ResponseEntity.status(401)
                    .body(Map.of("message", "아이디 또는 비밀번호가 일치하지 않습니다."));
        }

        session.setAttribute("loginMember", member);
        return ResponseEntity.ok(new LoginResponse(member.getLoginId(), member.getName()));
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout(HttpSession session) {
        session.invalidate();
        return ResponseEntity.ok(Map.of("message", "로그아웃 되었습니다."));
    }

    @GetMapping("/check")
    public ResponseEntity<?> check(HttpSession session) {
        MemberDTO member = (MemberDTO) session.getAttribute("loginMember");
        if (member == null) {
            return ResponseEntity.status(401)
                    .body(Map.of("message", "로그인이 필요합니다."));
        }
        return ResponseEntity.ok(new LoginResponse(member.getLoginId(), member.getName()));
    }

    @GetMapping("/check-username")
    public ResponseEntity<?> checkUsername(@RequestParam String username) {
        boolean exists = memberService.existsByLoginId(username);
        return ResponseEntity.ok(Map.of("exists", exists));
    }

    @PostMapping("/find-id")
    public ResponseEntity<?> findId(@RequestBody Map<String, String> request) {
        String name = request.get("name");
        String email = request.get("email");

        if (name == null || !name.trim().matches("^[가-힣a-zA-Z]{2,}$")) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "이름은 2자 이상 한글 또는 영문만 입력하세요."));
        }
        if (!isValidEmail(email)) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "올바른 이메일 형식을 입력하세요."));
        }

        MemberDTO member = memberService.findByNameAndEmail(name, email);
        if (member == null) {
            return ResponseEntity.status(404)
                    .body(Map.of("message", "일치하는 계정을 찾을 수 없습니다."));
        }

        String loginId = member.getLoginId();
        String masked = loginId.substring(0, Math.min(2, loginId.length()))
                + "*".repeat(Math.max(0, loginId.length() - 2));

        return ResponseEntity.ok(Map.of("username", masked));
    }

    @PostMapping("/verify-reset")
    public ResponseEntity<?> verifyReset(@RequestBody Map<String, String> request) {
        String username = request.get("username");
        String email = request.get("email");

        if (username == null || username.isBlank()) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "아이디를 입력하세요."));
        }
        if (!isValidEmail(email)) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "올바른 이메일 형식을 입력하세요."));
        }

        MemberDTO member = memberService.findByLoginIdAndEmail(username, email);
        if (member == null) {
            return ResponseEntity.status(404)
                    .body(Map.of("message", "일치하는 계정을 찾을 수 없습니다."));
        }

        return ResponseEntity.ok(Map.of("verified", true));
    }

    @PostMapping("/reset-password")
    public ResponseEntity<?> resetPassword(@RequestBody Map<String, String> request) {
        String username = request.get("username");
        String email = request.get("email");
        String newPassword = request.get("newPassword");

        if (username == null || username.isBlank()) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "아이디를 입력하세요."));
        }
        if (!isValidEmail(email)) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "올바른 이메일 형식을 입력하세요."));
        }
        if (!isValidPassword(newPassword)) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "비밀번호는 8~16자, 영문 대/소문자, 숫자, 특수문자를 포함해야 합니다."));
        }

        MemberDTO member = memberService.findByLoginIdAndEmail(username, email);
        if (member == null) {
            return ResponseEntity.status(404)
                    .body(Map.of("message", "일치하는 계정을 찾을 수 없습니다."));
        }

        memberService.changePassword(username, newPassword);
        return ResponseEntity.ok(Map.of("message", "비밀번호가 재설정되었습니다."));
    }

    @PostMapping("/signup")
    public ResponseEntity<?> signup(@RequestBody SignupRequest request) {
        if (request.getUsername() == null || request.getUsername().length() < 4) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "아이디는 4자 이상이어야 합니다."));
        }
        if (!isValidPassword(request.getPassword())) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "비밀번호는 8~16자, 영문 대/소문자, 숫자, 특수문자를 포함해야 합니다."));
        }
        if (request.getName() == null || !request.getName().trim().matches("^[가-힣a-zA-Z]{2,}$")) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "이름은 2자 이상 한글 또는 영문만 입력하세요."));
        }
        if (!isValidEmail(request.getEmail())) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "올바른 이메일을 입력하세요."));
        }
        if (memberService.existsByLoginId(request.getUsername())) {
            return ResponseEntity.status(409)
                    .body(Map.of("message", "이미 사용 중인 아이디입니다."));
        }

        memberService.signup(
                request.getUsername(),
                request.getPassword(),
                request.getName(),
                request.getEmail()
        );
        return ResponseEntity.ok(Map.of("message", "회원가입이 완료되었습니다."));
    }

    @PostMapping("/send-code")
    public ResponseEntity<?> sendCode(@RequestBody Map<String, String> request) {
        String email = request.get("email");
        if (!isValidEmail(email)) {
            return ResponseEntity.badRequest()
                    .body(Map.of("message", "올바른 이메일 형식을 입력하세요."));
        }
        try {
            emailService.sendVerificationCode(email);
            return ResponseEntity.ok(Map.of("message", "인증코드가 발송되었습니다."));
        } catch (Exception e) {
            return ResponseEntity.status(500)
                    .body(Map.of("message", "이메일 발송에 실패했습니다."));
        }
    }

    @PostMapping("/verify-code")
    public ResponseEntity<?> verifyCode(@RequestBody Map<String, String> request) {
        String email = request.get("email");
        String code = request.get("code");
        if (emailService.verifyCode(email, code)) {
            return ResponseEntity.ok(Map.of("verified", true));
        }
        return ResponseEntity.badRequest()
                .body(Map.of("message", "인증코드가 일치하지 않거나 만료되었습니다."));
    }

    @PostMapping("/find-id-full")
    public ResponseEntity<?> findIdFull(@RequestBody Map<String, String> request) {
        String name = request.get("name");
        String email = request.get("email");

        MemberDTO member = memberService.findByNameAndEmail(name, email);
        if (member == null) {
            return ResponseEntity.status(404)
                    .body(Map.of("message", "일치하는 계정을 찾을 수 없습니다."));
        }
        return ResponseEntity.ok(Map.of("username", member.getLoginId()));
    }

    private boolean isValidEmail(String email) {
        return email != null && email.trim().matches(EMAIL_REGEX);
    }

    private boolean isValidPassword(String password) {
        return password != null
            && password.length() >= 8
            && password.length() <= 16
            && password.matches(".*[A-Z].*")
            && password.matches(".*[a-z].*")
            && password.matches(".*[0-9].*")
            && password.matches(".*[!@#$%^&*()_+\\-=\\[\\]{};':\"\\\\|,.<>/?].*");
    }
}
