package com.aipass.service;

import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class EmailService {

    private final JavaMailSender mailSender;
    private final Map<String, CodeEntry> codeStore = new ConcurrentHashMap<>();

    public EmailService(JavaMailSender mailSender) {
        this.mailSender = mailSender;
    }

    public void sendVerificationCode(String toEmail) {
        String code = generateCode();
        long expiresAt = System.currentTimeMillis() + 5 * 60 * 1000;
        codeStore.put(toEmail, new CodeEntry(code, expiresAt));

        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom("aipass.noreply@gmail.com");
        message.setTo(toEmail);
        message.setSubject("[AI-PASS] 이메일 인증코드");
        message.setText("인증코드: " + code + "\n\n5분 내에 입력해주세요.");

        mailSender.send(message);
    }

    public boolean verifyCode(String email, String code) {
        CodeEntry entry = codeStore.get(email);
        if (entry == null) return false;
        if (System.currentTimeMillis() > entry.expiresAt) {
            codeStore.remove(email);
            return false;
        }
        if (entry.code.equals(code)) {
            codeStore.remove(email);
            return true;
        }
        return false;
    }

    private String generateCode() {
        return String.format("%06d", new SecureRandom().nextInt(1000000));
    }

    private record CodeEntry(String code, long expiresAt) {}
}
