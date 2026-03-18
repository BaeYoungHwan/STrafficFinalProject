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

    public MemberDTO findByUsername(String username) {
        return memberMapper.findByUsername(username);
    }

    public boolean existsByUsername(String username) {
        return memberMapper.countByUsername(username) > 0;
    }

    public void signup(String username, String password, String name, String email) {
        MemberDTO member = new MemberDTO();
        member.setUsername(username);
        member.setPassword(passwordEncoder.encode(password));
        member.setName(name);
        member.setEmail(email);
        member.setRole("ADMIN");
        memberMapper.insertMember(member);
    }

    public boolean checkPassword(String rawPassword, String encodedPassword) {
        return passwordEncoder.matches(rawPassword, encodedPassword);
    }

    public MemberDTO findByNameAndEmail(String name, String email) {
        return memberMapper.findByNameAndEmail(name, email);
    }

    public MemberDTO findByUsernameAndEmail(String username, String email) {
        return memberMapper.findByUsernameAndEmail(username, email);
    }

    public void updateProfile(String username, String name, String email, String phone) {
        MemberDTO member = new MemberDTO();
        member.setUsername(username);
        member.setName(name);
        member.setEmail(email);
        member.setPhone(phone);
        memberMapper.updateMember(member);
    }

    public void changePassword(String username, String newPassword) {
        memberMapper.updatePassword(username, passwordEncoder.encode(newPassword));
    }

    public String resetPassword(String username) {
        String tempPassword = generateTempPassword();
        memberMapper.updatePassword(username, passwordEncoder.encode(tempPassword));
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
