package com.aipass.controller;

import com.aipass.dto.MemberDTO;
import com.aipass.service.MemberService;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/member")
public class MemberController {

    private final MemberService memberService;

    public MemberController(MemberService memberService) {
        this.memberService = memberService;
    }

    @GetMapping("/profile")
    public ResponseEntity<?> getProfile(HttpSession session) {
        MemberDTO member = (MemberDTO) session.getAttribute("loginMember");
        if (member == null) {
            return ResponseEntity.status(401)
                    .body(Map.of("message", "로그인이 필요합니다."));
        }

        MemberDTO fresh = memberService.findByLoginId(member.getLoginId());
        return ResponseEntity.ok(Map.of(
                "username", fresh.getLoginId(),
                "name", fresh.getName(),
                "email", fresh.getEmail(),
                "createdAt", fresh.getCreatedAt() != null ? fresh.getCreatedAt().toString() : ""
        ));
    }

    @PutMapping("/profile")
    public ResponseEntity<?> updateProfile(@RequestBody Map<String, String> request, HttpSession session) {
        MemberDTO member = (MemberDTO) session.getAttribute("loginMember");
        if (member == null) {
            return ResponseEntity.status(401)
                    .body(Map.of("message", "로그인이 필요합니다."));
        }

        String email = request.get("email");

        if (email == null || !email.contains("@")) {
            return ResponseEntity.badRequest().body(Map.of("message", "올바른 이메일을 입력하세요."));
        }

        memberService.updateEmail(member.getLoginId(), email);

        MemberDTO updated = memberService.findByLoginId(member.getLoginId());
        session.setAttribute("loginMember", updated);

        return ResponseEntity.ok(Map.of("message", "회원정보가 수정되었습니다."));
    }

    @PostMapping("/change-password")
    public ResponseEntity<?> changePassword(@RequestBody Map<String, String> request, HttpSession session) {
        MemberDTO member = (MemberDTO) session.getAttribute("loginMember");
        if (member == null) {
            return ResponseEntity.status(401)
                    .body(Map.of("message", "로그인이 필요합니다."));
        }

        String newPassword = request.get("newPassword");

        if (newPassword == null || newPassword.length() < 8) {
            return ResponseEntity.badRequest().body(Map.of("message", "새 비밀번호는 8자 이상이어야 합니다."));
        }
        if (!newPassword.matches(".*[A-Z].*")) {
            return ResponseEntity.badRequest().body(Map.of("message", "새 비밀번호에 대문자를 포함해야 합니다."));
        }
        if (!newPassword.matches(".*[a-z].*")) {
            return ResponseEntity.badRequest().body(Map.of("message", "새 비밀번호에 소문자를 포함해야 합니다."));
        }
        if (!newPassword.matches(".*[0-9].*")) {
            return ResponseEntity.badRequest().body(Map.of("message", "새 비밀번호에 숫자를 포함해야 합니다."));
        }
        if (!newPassword.matches(".*[!@#$%^&*()_+\\-=\\[\\]{};':\"\\\\|,.<>/?].*")) {
            return ResponseEntity.badRequest().body(Map.of("message", "새 비밀번호에 특수문자를 포함해야 합니다."));
        }

        memberService.changePassword(member.getLoginId(), newPassword);
        return ResponseEntity.ok(Map.of("message", "비밀번호가 변경되었습니다."));
    }
}
