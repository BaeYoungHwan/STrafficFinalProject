package com.aipass.dao;

import com.aipass.dto.NotificationDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface NotificationMapper {
    void insert(NotificationDTO dto);
    List<NotificationDTO> findRecent(@Param("limit") int limit);
    int countUnread();
    void markAsRead(@Param("id") Long id);
    void markAllRead();
}
