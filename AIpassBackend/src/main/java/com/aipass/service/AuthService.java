package com.aipass.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.aipass.dao.AdminUserDao;
import com.aipass.dto.AdminUserDto;
import com.aipass.dto.LoginRequestDto;

@Service
public class AuthService {

    @Autowired
    private AdminUserDao adminUserDao;

    public AdminUserDto login(LoginRequestDto loginRequestDto) {
        AdminUserDto param = new AdminUserDto();
        param.setLoginId(loginRequestDto.getLoginId());
        param.setPassword(loginRequestDto.getPassword());

        return adminUserDao.login(param);
    }

    public boolean signup(AdminUserDto adminUserDto) {
        AdminUserDto existingUser = adminUserDao.findByLoginId(adminUserDto.getLoginId());

        if (existingUser != null) {
            return false;
        }

        return adminUserDao.insertAdminUser(adminUserDto) > 0;
    }
}