package com.aipass.controller;

import com.aipass.dao.NotificationMapper;
import com.aipass.dto.NotificationDTO;
import com.aipass.service.NotificationService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/notifications")
public class NotificationController {

    private final NotificationService notificationService;
    private final NotificationMapper notificationMapper;

    public NotificationController(NotificationService notificationService,
                                  NotificationMapper notificationMapper) {
        this.notificationService = notificationService;
        this.notificationMapper = notificationMapper;
    }

    /**
     * SSE 구독 엔드포인트 — 클라이언트가 5분마다 재연결
     */
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream() {
        return notificationService.subscribe();
    }

    /**
     * 최근 알림 50건 + 미읽음 개수 반환
     * 응답: {"success":true,"data":{"items":[...],"unreadCount":3}}
     */
    @GetMapping
    public ResponseEntity<?> getNotifications() {
        List<NotificationDTO> items = notificationMapper.findRecent(50);
        int unreadCount = notificationMapper.countUnread();

        Map<String, Object> data = new HashMap<>();
        data.put("items", items);
        data.put("unreadCount", unreadCount);

        return ResponseEntity.ok(Map.of("success", true, "data", data));
    }

    /**
     * 특정 알림 읽음 처리
     */
    @PutMapping("/{id}/read")
    public ResponseEntity<?> markAsRead(@PathVariable Long id) {
        notificationMapper.markAsRead(id);
        return ResponseEntity.ok(Map.of("success", true));
    }

    /**
     * 전체 알림 읽음 처리
     */
    @PutMapping("/read-all")
    public ResponseEntity<?> markAllRead() {
        notificationMapper.markAllRead();
        return ResponseEntity.ok(Map.of("success", true));
    }

    /**
     * 수동 알림 생성 (예지보전 모듈 등 외부 연동용)
     */
    @PostMapping
    public ResponseEntity<?> createNotification(@RequestBody Map<String, Object> body) {
        String eventType = (String) body.getOrDefault("eventType", "EQUIPMENT_FAILURE");
        String title = (String) body.get("title");
        String message = (String) body.get("message");
        Long relatedId = body.get("relatedId") instanceof Number
                ? ((Number) body.get("relatedId")).longValue()
                : null;

        notificationService.createAndBroadcast(eventType, title, message, relatedId);
        return ResponseEntity.ok(Map.of("success", true));
    }
}
