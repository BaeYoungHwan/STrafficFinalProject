package com.aipass.dao;

import org.apache.ibatis.annotations.Mapper;
import org.springframework.stereotype.Repository;
import com.aipass.dto.PriorityRouteIntersectionDto;

/*
 * [PriorityRouteDao]
 * MyBatis Mapper 인터페이스
 *
 * intersection 테이블에서
 * 교차로 좌표와 이름 조회
 */

@Mapper
@Repository
public interface PriorityRouteDao {

    // 교차로 ID로 교차로 정보 조회
    PriorityRouteIntersectionDto getIntersectionById(Long intersectionId);

}