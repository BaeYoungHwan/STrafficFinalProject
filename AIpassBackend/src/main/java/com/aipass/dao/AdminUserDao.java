package com.aipass.dao;

import org.apache.ibatis.annotations.Mapper;
import org.springframework.stereotype.Repository;

import com.aipass.dto.AdminUserDto;

@Mapper
@Repository
public interface AdminUserDao {
    AdminUserDto login(AdminUserDto adminUserDto);
    AdminUserDto findByLoginId(String loginId);
    int insertAdminUser(AdminUserDto adminUserDto);
}