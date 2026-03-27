package com.aipass.dao;

import com.aipass.dto.MemberDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface MemberMapper {
    MemberDTO findByLoginId(String loginId);
    int insertMember(MemberDTO member);
    int countByLoginId(String loginId);
    MemberDTO findByNameAndEmail(@Param("name") String name, @Param("email") String email);
    MemberDTO findByLoginIdAndEmail(@Param("loginId") String loginId, @Param("email") String email);
    int updatePassword(@Param("loginId") String loginId, @Param("password") String password);
    int updateMember(MemberDTO member);
    int updateEmail(@Param("loginId") String loginId, @Param("email") String email);
}
