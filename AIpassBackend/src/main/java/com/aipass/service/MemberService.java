package com.aipass.service;

import com.aipass.dao.MemberMapper;
import com.aipass.dto.MemberDTO;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class MemberService {

    private final MemberMapper memberMapper;
    private final BCryptPasswordEncoder passwordEncoder;

    public MemberService(MemberMapper memberMapper, BCryptPasswordEncoder passwordEncoder) {
        this.memberMapper = memberMapper;
        this.passwordEncoder = passwordEncoder;
    }

    public MemberDTO findByLoginId(String loginId) {
        return memberMapper.findByLoginId(loginId);
    }

    public boolean existsByLoginId(String loginId) {
        return memberMapper.countByLoginId(loginId) > 0;
    }

    public void signup(String loginId, String password, String name, String email) {
        MemberDTO member = new MemberDTO();
        member.setLoginId(loginId);
        member.setPassword(passwordEncoder.encode(password));
        member.setName(name);
        member.setEmail(email);
        memberMapper.insertMember(member);
    }

    public boolean checkPassword(String rawPassword, String encodedPassword) {
        return passwordEncoder.matches(rawPassword, encodedPassword);
    }

    public MemberDTO findByNameAndEmail(String name, String email) {
        return memberMapper.findByNameAndEmail(name, email);
    }

    public MemberDTO findByLoginIdAndEmail(String loginId, String email) {
        return memberMapper.findByLoginIdAndEmail(loginId, email);
    }

    public void updateProfile(String loginId, String name, String email) {
        MemberDTO member = new MemberDTO();
        member.setLoginId(loginId);
        member.setName(name);
        member.setEmail(email);
        memberMapper.updateMember(member);
    }

    public void updateEmail(String loginId, String email) {
        memberMapper.updateEmail(loginId, email);
    }

    public void changePassword(String loginId, String newPassword) {
        memberMapper.updatePassword(loginId, passwordEncoder.encode(newPassword));
    }

    public String resetPassword(String loginId) {
        String tempPassword = generateTempPassword();
        memberMapper.updatePassword(loginId, passwordEncoder.encode(tempPassword));
        return tempPassword;
    }

    private String generateTempPassword() {
        String chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$";
        StringBuilder sb = new StringBuilder();
        java.util.Random random = new java.security.SecureRandom();
        for (int i = 0; i < 12; i++) {
            sb.append(chars.charAt(random.nextInt(chars.length())));
        }
        return sb.toString();
    }
}
