package com.aipass.dao;

import com.aipass.dto.MemberDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface MemberMapper {
    MemberDTO findByUsername(String username);
    int insertMember(MemberDTO member);
    int countByUsername(String username);
    MemberDTO findByNameAndEmail(@Param("name") String name, @Param("email") String email);
    MemberDTO findByUsernameAndEmail(@Param("username") String username, @Param("email") String email);
    int updatePassword(@Param("username") String username, @Param("password") String password);
    int updateMember(MemberDTO member);
}
