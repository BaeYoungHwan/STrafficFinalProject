package com.aipass;

import com.aipass.controller.CctvController;
import com.aipass.dao.CctvMapper;
import com.aipass.dto.CctvDTO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * CctvController 단위 테스트
 *
 * Spring Boot 4.x 이므로 @MockitoBean 사용
 * (org.springframework.test.context.bean.override.mockito)
 *
 * CCTV 엔드포인트는 세션 인증 없이 공개 접근 가능하므로
 * LoginInterceptor는 통과(true)로만 stub 처리한다.
 */
@WebMvcTest(CctvController.class)
class CctvControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private CctvMapper cctvMapper;

    // WebConfigurer가 LoginInterceptor를 등록하므로
    // @WebMvcTest 컨텍스트에서도 인터셉터가 활성화된다.
    @MockitoBean
    private LoginInterceptor loginInterceptor;

    @BeforeEach
    void setUp() throws Exception {
        // CCTV 엔드포인트는 세션 검사를 하지 않으므로 항상 통과
        when(loginInterceptor.preHandle(any(), any(), any())).thenReturn(true);
    }

    // =========================================================================
    // GET /api/cctv/list
    // =========================================================================

    @Test
    @DisplayName("getCctvList_ActiveCctvExists_Returns200WithData: 활성 CCTV 존재 시 200과 목록 반환")
    void getCctvList_ActiveCctvExists_Returns200WithData() throws Exception {
        CctvDTO dto1 = buildDto("CCTV-001", "교차로A 카메라", "강남대로", "http://stream1.example.com/live", "강남구");
        CctvDTO dto2 = buildDto("CCTV-002", "교차로B 카메라", "테헤란로", "http://stream2.example.com/live", "서초구");

        when(cctvMapper.findAllActive()).thenReturn(List.of(dto1, dto2));

        mockMvc.perform(get("/api/cctv/list"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data").isArray())
                .andExpect(jsonPath("$.data.length()").value(2))
                .andExpect(jsonPath("$.data[0].cctvId").value("CCTV-001"))
                .andExpect(jsonPath("$.data[0].displayUrl").value("http://localhost:8000/api/v1/stream/video"))
                .andExpect(jsonPath("$.data[1].cctvId").value("CCTV-002"))
                .andExpect(jsonPath("$.data[1].displayUrl").value("http://localhost:8000/api/v1/stream/video"));
    }

    @Test
    @DisplayName("getCctvList_NoCctvExists_Returns200WithEmptyList: 활성 CCTV 없을 때 200과 빈 배열 반환")
    void getCctvList_NoCctvExists_Returns200WithEmptyList() throws Exception {
        when(cctvMapper.findAllActive()).thenReturn(List.of());

        mockMvc.perform(get("/api/cctv/list"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data").isArray())
                .andExpect(jsonPath("$.data.length()").value(0));
    }

    @Test
    @DisplayName("getCctvList_MapperThrows_Returns500: 매퍼 예외 발생 시 500과 success:false 반환")
    void getCctvList_MapperThrows_Returns500() throws Exception {
        when(cctvMapper.findAllActive()).thenThrow(new RuntimeException("DB 연결 실패"));

        mockMvc.perform(get("/api/cctv/list"))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").value("CCTV 목록 조회 중 오류가 발생했습니다."));
    }

    // =========================================================================
    // GET /api/cctv/ai-target
    // =========================================================================

    @Test
    @DisplayName("getAiTargetCctv_ActiveCctvExists_Returns200WithUrlAndId: 활성 CCTV 존재 시 url과 cctvId 포함하여 반환")
    void getAiTargetCctv_ActiveCctvExists_Returns200WithUrlAndId() throws Exception {
        CctvDTO dto = buildDto("CCTV-001", "교차로A 카메라", "강남대로", "http://stream1.example.com/live", "강남구");

        when(cctvMapper.findAiTargetCctv()).thenReturn(dto);

        mockMvc.perform(get("/api/cctv/ai-target"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.url").value("http://stream1.example.com/live"))
                .andExpect(jsonPath("$.data.cctvId").value("CCTV-001"));
    }

    @Test
    @DisplayName("getAiTargetCctv_NoCctvExists_Returns200WithSuccessFalse: 활성 CCTV 없으면 success:false와 메시지 반환")
    void getAiTargetCctv_NoCctvExists_Returns200WithSuccessFalse() throws Exception {
        // findAiTargetCctv()가 null 반환 — DB에 활성 CCTV 없는 상황
        when(cctvMapper.findAiTargetCctv()).thenReturn(null);

        mockMvc.perform(get("/api/cctv/ai-target"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").value("활성 CCTV 없음"));
    }

    @Test
    @DisplayName("getAiTargetCctv_MapperThrows_Returns500: 매퍼 예외 발생 시 500과 success:false 반환")
    void getAiTargetCctv_MapperThrows_Returns500() throws Exception {
        when(cctvMapper.findAiTargetCctv()).thenThrow(new RuntimeException("쿼리 타임아웃"));

        mockMvc.perform(get("/api/cctv/ai-target"))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").value("AI 대상 CCTV 조회 중 오류가 발생했습니다."));
    }

    // =========================================================================
    // GET /api/cctv/{id}
    // =========================================================================

    @Test
    @DisplayName("getCctv_ExistingId_Returns200WithData: 존재하는 ID 요청 시 200과 CCTV 데이터 반환")
    void getCctv_ExistingId_Returns200WithData() throws Exception {
        CctvDTO dto = buildDto("CCTV-001", "교차로A 카메라", "강남대로", "http://stream1.example.com/live", "강남구");

        when(cctvMapper.findById(eq("CCTV-001"))).thenReturn(dto);

        mockMvc.perform(get("/api/cctv/CCTV-001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.cctvId").value("CCTV-001"))
                .andExpect(jsonPath("$.data.cctvName").value("교차로A 카메라"))
                .andExpect(jsonPath("$.data.streamUrl").value("http://stream1.example.com/live"))
                .andExpect(jsonPath("$.data.displayUrl").value("http://localhost:8000/api/v1/stream/video"));
    }

    @Test
    @DisplayName("getCctv_NonExistingId_Returns404WithSuccessFalse: 존재하지 않는 ID 요청 시 404와 success:false 반환")
    void getCctv_NonExistingId_Returns404WithSuccessFalse() throws Exception {
        // findById가 null 반환 — 해당 ID가 DB에 없는 상황
        when(cctvMapper.findById(eq("CCTV-999"))).thenReturn(null);

        mockMvc.perform(get("/api/cctv/CCTV-999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").value("해당 CCTV를 찾을 수 없습니다."));
    }

    @Test
    @DisplayName("getCctv_MapperThrows_Returns500: 매퍼 예외 발생 시 500과 success:false 반환")
    void getCctv_MapperThrows_Returns500() throws Exception {
        when(cctvMapper.findById(any())).thenThrow(new RuntimeException("DB 오류"));

        mockMvc.perform(get("/api/cctv/CCTV-ERR"))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").value("CCTV 조회 중 오류가 발생했습니다."));
    }

    // =========================================================================
    // 헬퍼 메서드
    // =========================================================================

    /**
     * 테스트용 CctvDTO 픽스처 생성.
     */
    private CctvDTO buildDto(String cctvId, String cctvName, String roadName, String streamUrl, String district) {
        CctvDTO dto = new CctvDTO();
        dto.setCctvId(cctvId);
        dto.setCctvName(cctvName);
        dto.setRoadName(roadName);
        dto.setStreamUrl(streamUrl);
        dto.setDisplayUrl("http://localhost:8000/api/v1/stream/video");
        dto.setDistrict(district);
        dto.setLatitude(37.4979);
        dto.setLongitude(127.0276);
        dto.setIsActive(true);
        dto.setUpdatedAt("26-03-24 12:00:00");
        return dto;
    }
}
