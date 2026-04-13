package com.aipass.service;

import com.aipass.dao.NotificationMapper;
import com.aipass.dto.NotificationDTO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.lang.reflect.Field;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

/**
 * NotificationService 단위 테스트
 *
 * - @ExtendWith(MockitoExtension.class) : 순수 Mockito 기반, Spring 컨텍스트 불필요
 * - private emitters 필드 접근은 reflection 사용
 * - SseEmitter.send() 는 final 메서드이므로 직접 spy 불가 → mock으로 대체
 */
@ExtendWith(MockitoExtension.class)
class NotificationServiceTest {

    @Mock
    private NotificationMapper notificationMapper;

    @InjectMocks
    private NotificationService notificationService;

    // =========================================================================
    // 헬퍼: reflection으로 private 필드 접근
    // =========================================================================

    @SuppressWarnings("unchecked")
    private CopyOnWriteArrayList<SseEmitter> getEmitters() throws Exception {
        Field field = NotificationService.class.getDeclaredField("emitters");
        field.setAccessible(true);
        return (CopyOnWriteArrayList<SseEmitter>) field.get(notificationService);
    }

    /**
     * SseEmitter의 onCompletion 콜백 Runnable을 reflection으로 꺼내 직접 실행한다.
     * 테스트 환경에서는 Servlet 컨테이너(handler)가 없어 complete() 호출만으로는
     * 콜백이 실행되지 않으므로 이 방식으로 검증한다.
     */
    private void triggerCompletionCallback(SseEmitter emitter) throws Exception {
        // ResponseBodyEmitter.completionCallback (DefaultCallback implements Runnable)
        Field cbField = emitter.getClass().getSuperclass().getDeclaredField("completionCallback");
        cbField.setAccessible(true);
        Runnable callback = (Runnable) cbField.get(emitter);
        callback.run();
    }

    /**
     * SseEmitter의 onError 콜백 Consumer를 reflection으로 꺼내 직접 실행한다.
     */
    @SuppressWarnings("unchecked")
    private void triggerErrorCallback(SseEmitter emitter, Throwable ex) throws Exception {
        // ResponseBodyEmitter.errorCallback (ErrorCallback implements Consumer<Throwable>)
        Field cbField = emitter.getClass().getSuperclass().getDeclaredField("errorCallback");
        cbField.setAccessible(true);
        java.util.function.Consumer<Throwable> callback =
                (java.util.function.Consumer<Throwable>) cbField.get(emitter);
        callback.accept(ex);
    }

    @BeforeEach
    void clearEmitters() throws Exception {
        // 각 테스트가 독립적으로 실행되도록 emitters 목록을 비운다
        getEmitters().clear();
    }

    // =========================================================================
    // subscribe()
    // =========================================================================

    @Test
    @DisplayName("subscribe_returnsEmitter: subscribe() 반환값이 null이 아닌 SseEmitter인지 확인")
    void subscribe_returnsEmitter() {
        SseEmitter emitter = notificationService.subscribe();

        assertThat(emitter).isNotNull();
        assertThat(emitter).isInstanceOf(SseEmitter.class);
    }

    @Test
    @DisplayName("subscribe_emitterAddedToList: subscribe() 후 내부 emitters 리스트 크기가 1 증가하는지 확인")
    void subscribe_emitterAddedToList() throws Exception {
        int before = getEmitters().size(); // 0

        notificationService.subscribe();

        assertThat(getEmitters().size()).isEqualTo(before + 1);
    }

    @Test
    @DisplayName("subscribe_multipleSubscribers_allAddedToList: 구독자가 여럿일 때 emitters 목록 크기가 구독 횟수만큼 증가")
    void subscribe_multipleSubscribers_allAddedToList() throws Exception {
        notificationService.subscribe();
        notificationService.subscribe();
        notificationService.subscribe();

        assertThat(getEmitters().size()).isEqualTo(3);
    }

    @Test
    @DisplayName("subscribe_onCompletion_removesEmitterFromList: 완료 콜백 실행 시 emitters 목록에서 제거")
    void subscribe_onCompletion_removesEmitterFromList() throws Exception {
        SseEmitter emitter = notificationService.subscribe();
        assertThat(getEmitters()).contains(emitter);

        // 테스트 환경에서는 Servlet handler가 없으므로 완료 콜백 Runnable을 직접 실행
        triggerCompletionCallback(emitter);

        assertThat(getEmitters()).doesNotContain(emitter);
    }

    @Test
    @DisplayName("subscribe_onError_removesEmitterFromList: 에러 콜백 실행 시 emitters 목록에서 제거")
    void subscribe_onError_removesEmitterFromList() throws Exception {
        SseEmitter emitter = notificationService.subscribe();
        assertThat(getEmitters()).contains(emitter);

        // 테스트 환경에서는 Servlet handler가 없으므로 에러 콜백 Consumer를 직접 실행
        triggerErrorCallback(emitter, new Exception("connection error"));

        assertThat(getEmitters()).doesNotContain(emitter);
    }

    // =========================================================================
    // createAndBroadcast()
    // =========================================================================

    @Test
    @DisplayName("createAndBroadcast_callsMapperInsert: notificationMapper.insert()가 정확히 1회 호출되는지 검증")
    void createAndBroadcast_callsMapperInsert() {
        notificationService.createAndBroadcast("SPEED", "제목", "메시지", 1L);

        verify(notificationMapper, times(1)).insert(any(NotificationDTO.class));
    }

    @Test
    @DisplayName("createAndBroadcast_setsFieldsCorrectly: insert()에 전달된 DTO의 필드가 입력값과 일치하는지 ArgumentCaptor로 검증")
    void createAndBroadcast_setsFieldsCorrectly() {
        ArgumentCaptor<NotificationDTO> captor = ArgumentCaptor.forClass(NotificationDTO.class);

        notificationService.createAndBroadcast("SPEED", "과속 감지", "50km/h 구간에서 80km/h 감지", 42L);

        verify(notificationMapper).insert(captor.capture());
        NotificationDTO captured = captor.getValue();

        assertThat(captured.getEventType()).isEqualTo("SPEED");
        assertThat(captured.getTitle()).isEqualTo("과속 감지");
        assertThat(captured.getMessage()).isEqualTo("50km/h 구간에서 80km/h 감지");
        assertThat(captured.getRelatedId()).isEqualTo(42L);
    }

    @Test
    @DisplayName("createAndBroadcast_relatedIdNull_insertsWithNullRelatedId: relatedId가 null이어도 insert 호출되고 DTO에 null로 세팅")
    void createAndBroadcast_relatedIdNull_insertsWithNullRelatedId() {
        ArgumentCaptor<NotificationDTO> captor = ArgumentCaptor.forClass(NotificationDTO.class);

        notificationService.createAndBroadcast("SYSTEM", "시스템 알림", "서버 점검", null);

        verify(notificationMapper).insert(captor.capture());
        assertThat(captor.getValue().getRelatedId()).isNull();
    }

    @Test
    @DisplayName("createAndBroadcast_noSubscribers_doesNotThrow: 구독자가 없어도 예외 없이 완료")
    void createAndBroadcast_noSubscribers_doesNotThrow() {
        // emitters 목록이 비어 있으면 broadcast 루프가 돌지 않는다
        // 예외가 없으면 테스트 통과
        notificationService.createAndBroadcast("LINE", "실선 침범", "1번 카메라 감지", 5L);

        verify(notificationMapper, times(1)).insert(any(NotificationDTO.class));
    }

    // =========================================================================
    // broadcast() — 실패한 emitter 제거 검증
    // =========================================================================

    @Test
    @DisplayName("broadcast_removesFailedEmitter: send() 중 IOException이 발생한 emitter는 목록에서 제거")
    void broadcast_removesFailedEmitter() throws Exception {
        // SseEmitter를 mock으로 교체하여 send() 시 IOException을 강제 발생
        SseEmitter failingEmitter = mock(SseEmitter.class);
        doThrow(new IOException("연결 끊김"))
                .when(failingEmitter).send(any(SseEmitter.SseEventBuilder.class));

        // 직접 emitters 목록에 mock emitter 추가
        getEmitters().add(failingEmitter);
        assertThat(getEmitters()).hasSize(1);

        // broadcast는 createAndBroadcast 내부에서 호출됨
        notificationService.createAndBroadcast("SPEED", "제목", "내용", 1L);

        // IOException이 발생한 emitter는 목록에서 제거되어야 한다
        assertThat(getEmitters()).doesNotContain(failingEmitter);
    }

    @Test
    @DisplayName("broadcast_keepsSucessfulEmitter_removesOnlyFailed: 정상 emitter는 유지, 실패한 emitter만 제거")
    void broadcast_keepsSucessfulEmitter_removesOnlyFailed() throws Exception {
        SseEmitter goodEmitter = mock(SseEmitter.class);
        SseEmitter failingEmitter = mock(SseEmitter.class);

        // goodEmitter — send() 정상 처리 (doNothing 기본 동작)
        doNothing().when(goodEmitter).send(any(SseEmitter.SseEventBuilder.class));
        doThrow(new IOException("연결 끊김"))
                .when(failingEmitter).send(any(SseEmitter.SseEventBuilder.class));

        getEmitters().add(goodEmitter);
        getEmitters().add(failingEmitter);

        notificationService.createAndBroadcast("LINE", "제목", "내용", 2L);

        assertThat(getEmitters()).contains(goodEmitter);
        assertThat(getEmitters()).doesNotContain(failingEmitter);
        assertThat(getEmitters()).hasSize(1);
    }

    @Test
    @DisplayName("broadcast_multipleEmitters_sendsToAll: 정상 구독자 여럿에게 모두 send() 호출 확인")
    void broadcast_multipleEmitters_sendsToAll() throws Exception {
        SseEmitter emitter1 = mock(SseEmitter.class);
        SseEmitter emitter2 = mock(SseEmitter.class);
        SseEmitter emitter3 = mock(SseEmitter.class);

        doNothing().when(emitter1).send(any(SseEmitter.SseEventBuilder.class));
        doNothing().when(emitter2).send(any(SseEmitter.SseEventBuilder.class));
        doNothing().when(emitter3).send(any(SseEmitter.SseEventBuilder.class));

        getEmitters().add(emitter1);
        getEmitters().add(emitter2);
        getEmitters().add(emitter3);

        notificationService.createAndBroadcast("SPEED", "다중 전송", "내용", 10L);

        // 각 emitter에 정확히 1회씩 send() 호출
        verify(emitter1, times(1)).send(any(SseEmitter.SseEventBuilder.class));
        verify(emitter2, times(1)).send(any(SseEmitter.SseEventBuilder.class));
        verify(emitter3, times(1)).send(any(SseEmitter.SseEventBuilder.class));
    }
}
