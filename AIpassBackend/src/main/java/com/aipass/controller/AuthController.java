package com.aipass.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import com.aipass.dto.AdminUserDto;
import com.aipass.dto.LoginRequestDto;
import com.aipass.service.AuthService;

@RestController
@RequestMapping("/auth")
@CrossOrigin(origins = "*")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/login")
    public AdminUserDto login(@RequestBody LoginRequestDto loginRequestDto) {
        return authService.login(loginRequestDto);
    }

    @PostMapping("/signup")
    public boolean signup(@RequestBody AdminUserDto adminUserDto) {
        return authService.signup(adminUserDto);
    }
}