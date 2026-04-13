package com.aipass.service;

import com.aipass.dao.NotificationMapper;
import com.aipass.dto.NotificationDTO;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

@Service
public class NotificationService {

    private static final Logger logger = LoggerFactory.getLogger(NotificationService.class);

    private final CopyOnWriteArrayList<SseEmitter> emitters = new CopyOnWriteArrayList<>();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @PostConstruct
    public void startHeartbeat() {
        Executors.newSingleThreadScheduledExecutor().scheduleAtFixedRate(() -> {
            for (SseEmitter emitter : emitters) {
                try {
                    emitter.send(SseEmitter.event().name("ping").data(""));
                } catch (IOException e) {
                    emitters.remove(emitter);
                }
            }
        }, 30, 30, TimeUnit.SECONDS);
    }

    @Autowired
    private NotificationMapper notificationMapper;

    /**
     * SSE 구독 등록 (타임아웃 5분)
     */
    public SseEmitter subscribe() {
        SseEmitter emitter = new SseEmitter(Long.MAX_VALUE);
        emitters.add(emitter);
        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> emitters.remove(emitter));
        emitter.onError(e -> emitters.remove(emitter));

        try {
            emitter.send(SseEmitter.event().name("connected").data("ok"));
        } catch (IOException e) {
            emitters.remove(emitter);
        }
        return emitter;
    }

    /**
     * DB 저장 후 모든 구독 클라이언트에 브로드캐스트
     */
    public void createAndBroadcast(String eventType, String title, String message, Long relatedId) {
        NotificationDTO dto = new NotificationDTO();
        dto.setEventType(eventType);
        dto.setTitle(title);
        dto.setMessage(message);
        dto.setRelatedId(relatedId);
        notificationMapper.insert(dto);
        broadcast(dto);
    }

    /**
     * 모든 연결된 클라이언트에 알림 이벤트 전송
     */
    private void broadcast(NotificationDTO dto) {
        String json;
        try {
            json = objectMapper.writeValueAsString(dto);
        } catch (Exception e) {
            logger.error("[SSE] JSON 직렬화 실패: {}", e.getMessage());
            return;
        }

        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event().name("notification").data(json));
            } catch (IOException e) {
                emitters.remove(emitter);
            }
        }
    }
}
