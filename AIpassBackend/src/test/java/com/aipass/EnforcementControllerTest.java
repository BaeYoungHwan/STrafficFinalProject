package com.aipass;

import com.aipass.controller.EnforcementController;
import com.aipass.dao.ViolationMapper;
import com.aipass.dto.ViolationDTO;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * EnforcementController 단위 테스트
 *
 * Spring Boot 4.x 이므로 @MockitoBean 사용
 * (org.springframework.test.context.bean.override.mockito)
 *
 * 세션 구조:
 *  - /api/enforcement/webhook  → LoginInterceptor 제외 (공개 엔드포인트)
 *  - 나머지 /api/enforcement/* → loginMember 세션 속성 필요
 */
@WebMvcTest(EnforcementController.class)
class EnforcementControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private ViolationMapper violationMapper;

    // WebConfigurer가 LoginInterceptor를 등록하므로
    // @WebMvcTest 컨텍스트에서도 인터셉터가 활성화된다.
    // LoginInterceptor 자체는 @Component로 자동 등록됨.
    @MockitoBean
    private LoginInterceptor loginInterceptor;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() throws Exception {
        // 기본값: 인터셉터가 세션 검사 없이 통과 (테스트별로 재정의 가능)
        when(loginInterceptor.preHandle(any(), any(), any())).thenReturn(true);
    }

    // =========================================================================
    // POST /api/enforcement/webhook  (공개 엔드포인트 — 세션 불필요)
    // =========================================================================

    @Test
    @DisplayName("webhook_ValidPayload_Returns200: 정상 페이로드 수신 시 200 반환, insert 1회 호출")
    void webhook_ValidPayload_Returns200() throws Exception {
        Map<String, Object> body = new HashMap<>();
        body.put("eventId", "EVT-001");
        body.put("plateNumber", "12가3456");
        body.put("imageUrl", "http://example.com/img.jpg");
        body.put("srcImageUrl", "http://example.com/src.jpg");
        body.put("violationType", "SPEEDING");
        body.put("speedKmh", 80.5);

        // insert()는 void 반환이므로 별도 stub 불필요 (doNothing이 기본값)

        mockMvc.perform(post("/api/enforcement/webhook")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true));

        // insert()가 정확히 1회 호출되었는지 검증
        verify(violationMapper, times(1)).insert(any(ViolationDTO.class));
    }

    @Test
    @DisplayName("webhook_MissingPlateNumber_DefaultsTo미인식: plateNumber 누락 시 '미인식'으로 저장")
    void webhook_MissingPlateNumber_DefaultsTo미인식() throws Exception {
        Map<String, Object> body = new HashMap<>();
        body.put("eventId", "EVT-002");
        // plateNumber 의도적으로 누락
        body.put("violationType", "RED_LIGHT");
        body.put("speedKmh", 0);

        mockMvc.perform(post("/api/enforcement/webhook")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true));

        // ArgumentCaptor로 실제 insert에 전달된 DTO를 캡처하여 plateNumber 검증
        ArgumentCaptor<ViolationDTO> captor = ArgumentCaptor.forClass(ViolationDTO.class);
        verify(violationMapper, times(1)).insert(captor.capture());
        assertThat(captor.getValue().getPlateNumber()).isEqualTo("미인식");
    }

    @Test
    @DisplayName("webhook_InsertFails_Returns500: insert에서 예외 발생 시 500 반환")
    void webhook_InsertFails_Returns500() throws Exception {
        Map<String, Object> body = new HashMap<>();
        body.put("eventId", "EVT-003");
        body.put("plateNumber", "99나9999");
        body.put("violationType", "SPEEDING");

        // insert 시 RuntimeException 발생 stub
        doThrow(new RuntimeException("DB 연결 실패"))
                .when(violationMapper).insert(any(ViolationDTO.class));

        mockMvc.perform(post("/api/enforcement/webhook")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").value("DB 연결 실패"));
    }

    // =========================================================================
    // GET /api/enforcement/violations  (세션 필요)
    // =========================================================================

    @Test
    @DisplayName("getViolations_WithSession_Returns200: 유효 세션으로 목록 조회 성공")
    void getViolations_WithSession_Returns200() throws Exception {
        // 세션이 있을 때 인터셉터 통과
        when(loginInterceptor.preHandle(any(), any(), any())).thenReturn(true);

        ViolationDTO dto = new ViolationDTO();
        dto.setViolationId(1L);
        dto.setPlateNumber("12가3456");
        dto.setViolationType("과속");
        dto.setFineStatus("UNPROCESSED");

        when(violationMapper.findAll(anyMap())).thenReturn(List.of(dto));
        when(violationMapper.countAll(anyMap())).thenReturn(1);

        mockMvc.perform(get("/api/enforcement/violations")
                        .sessionAttr("loginMember", "testUser"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.items[0].plateNumber").value("12가3456"))
                .andExpect(jsonPath("$.data.total").value(1));
    }

    @Test
    @DisplayName("getViolations_NoSession_Returns401: 세션 없이 요청 시 401 반환")
    void getViolations_NoSession_Returns401() throws Exception {
        // 세션이 없을 때 인터셉터가 401 응답 후 false 반환하도록 stub
        doAnswer(invocation -> {
            jakarta.servlet.http.HttpServletResponse resp =
                    invocation.getArgument(1);
            resp.setStatus(401);
            resp.setContentType("application/json;charset=UTF-8");
            resp.getWriter().write("{\"message\":\"로그인이 필요합니다.\"}");
            return false;
        }).when(loginInterceptor).preHandle(any(), any(), any());

        mockMvc.perform(get("/api/enforcement/violations"))
                // 세션 속성 없음
                .andExpect(status().isUnauthorized());
    }

    // =========================================================================
    // GET /api/enforcement/violations/{id}  (세션 필요)
    // =========================================================================

    @Test
    @DisplayName("getViolationById_WithSession_Returns200: 유효 세션으로 단건 조회 성공")
    void getViolationById_WithSession_Returns200() throws Exception {
        when(loginInterceptor.preHandle(any(), any(), any())).thenReturn(true);

        ViolationDTO dto = new ViolationDTO();
        dto.setViolationId(1L);
        dto.setPlateNumber("77다8888");
        dto.setViolationType("신호위반");
        dto.setFineStatus("APPROVED");

        when(violationMapper.findById(1L)).thenReturn(dto);

        mockMvc.perform(get("/api/enforcement/violations/1")
                        .sessionAttr("loginMember", "testUser"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.violationId").value(1))
                .andExpect(jsonPath("$.data.plateNumber").value("77다8888"));
    }

    // =========================================================================
    // PUT /api/enforcement/violations/{id}/status  (세션 필요)
    // =========================================================================

    @Test
    @DisplayName("updateStatus_Approved_CallsWithAPPROVED: '승인' 전달 시 DB에 APPROVED 로 전달")
    void updateStatus_Approved_CallsWithAPPROVED() throws Exception {
        when(loginInterceptor.preHandle(any(), any(), any())).thenReturn(true);

        ViolationDTO existing = new ViolationDTO();
        existing.setViolationId(1L);
        existing.setFineStatus("UNPROCESSED");
        when(violationMapper.findById(1L)).thenReturn(existing);

        Map<String, String> body = Map.of("status", "승인");

        mockMvc.perform(put("/api/enforcement/violations/1/status")
                        .sessionAttr("loginMember", "testUser")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true));

        // updateStatus가 "APPROVED"로 호출되었는지 검증
        verify(violationMapper, times(1)).updateStatus(eq(1L), eq("APPROVED"));
    }

    @Test
    @DisplayName("updateStatus_Rejected_CallsWithREJECTED: '반려' 전달 시 DB에 REJECTED 로 전달")
    void updateStatus_Rejected_CallsWithREJECTED() throws Exception {
        when(loginInterceptor.preHandle(any(), any(), any())).thenReturn(true);

        ViolationDTO existing = new ViolationDTO();
        existing.setViolationId(1L);
        existing.setFineStatus("UNPROCESSED");
        when(violationMapper.findById(1L)).thenReturn(existing);

        Map<String, String> body = Map.of("status", "반려");

        mockMvc.perform(put("/api/enforcement/violations/1/status")
                        .sessionAttr("loginMember", "testUser")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true));

        // updateStatus가 "REJECTED"로 호출되었는지 검증
        verify(violationMapper, times(1)).updateStatus(eq(1L), eq("REJECTED"));
    }

    // =========================================================================
    // PUT /api/enforcement/violations/{id}  (세션 필요)
    // =========================================================================

    @Test
    @DisplayName("updateViolation_CallsUpdateMapper: 수정 요청 시 update() 매퍼 호출 검증")
    void updateViolation_CallsUpdateMapper() throws Exception {
        when(loginInterceptor.preHandle(any(), any(), any())).thenReturn(true);

        ViolationDTO existing = new ViolationDTO();
        existing.setViolationId(1L);
        existing.setPlateNumber("00아0000");
        existing.setViolationType("과속");
        existing.setFineStatus("UNPROCESSED");
        when(violationMapper.findById(1L)).thenReturn(existing);

        Map<String, String> body = new HashMap<>();
        body.put("plateNumber", "11나1111");
        body.put("violationType", "신호위반");
        body.put("status", "승인");

        mockMvc.perform(put("/api/enforcement/violations/1")
                        .sessionAttr("loginMember", "testUser")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true));

        // update()가 정확히 1회 호출되었는지 검증
        ArgumentCaptor<ViolationDTO> captor = ArgumentCaptor.forClass(ViolationDTO.class);
        verify(violationMapper, times(1)).update(captor.capture());
        ViolationDTO updated = captor.getValue();
        assertThat(updated.getPlateNumber()).isEqualTo("11나1111");
        assertThat(updated.getViolationType()).isEqualTo("신호위반");
        assertThat(updated.getFineStatus()).isEqualTo("APPROVED");
    }
}
