package com.aipass.controller;

import com.aipass.dao.CctvMapper;
import com.aipass.dto.CctvDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/cctv")
public class CctvController {

    private static final Logger logger = LoggerFactory.getLogger(CctvController.class);

    private final CctvMapper cctvMapper;

    public CctvController(CctvMapper cctvMapper) {
        this.cctvMapper = cctvMapper;
    }

    /**
     * 활성 CCTV 목록 조회
     * GET /api/cctv/list
     */
    @GetMapping("/list")
    public ResponseEntity<?> getCctvList() {
        try {
            List<CctvDTO> data = cctvMapper.findAllActive();
            return ResponseEntity.ok(Map.of("success", true, "data", data));
        } catch (Exception e) {
            logger.error("[getCctvList] CCTV 목록 조회 실패: {}", e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of("success", false, "message", "CCTV 목록 조회 중 오류가 발생했습니다."));
        }
    }

    /**
     * AI 서버용 대상 CCTV 조회 (활성 CCTV 중 첫 번째)
     * GET /api/cctv/ai-target
     */
    @GetMapping("/ai-target")
    public ResponseEntity<?> getAiTargetCctv() {
        try {
            CctvDTO data = cctvMapper.findAiTargetCctv();
            if (data == null) {
                return ResponseEntity.ok(Map.of("success", false, "message", "활성 CCTV 없음"));
            }
            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "data", Map.of(
                            "url", data.getStreamUrl(),
                            "cctvId", data.getCctvId()
                    )
            ));
        } catch (Exception e) {
            logger.error("[getAiTargetCctv] AI 대상 CCTV 조회 실패: {}", e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of("success", false, "message", "AI 대상 CCTV 조회 중 오류가 발생했습니다."));
        }
    }

    /**
     * CCTV 단건 조회
     * GET /api/cctv/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<?> getCctv(@PathVariable String id) {
        try {
            CctvDTO data = cctvMapper.findById(id);
            if (data == null) {
                return ResponseEntity.status(404).body(Map.of("success", false, "message", "해당 CCTV를 찾을 수 없습니다."));
            }
            return ResponseEntity.ok(Map.of("success", true, "data", data));
        } catch (Exception e) {
            logger.error("[getCctv] CCTV 단건 조회 실패 id={}: {}", id, e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of("success", false, "message", "CCTV 조회 중 오류가 발생했습니다."));
        }
    }
}
