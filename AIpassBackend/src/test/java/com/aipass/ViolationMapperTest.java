package com.aipass;

import com.aipass.dao.ViolationMapper;
import com.aipass.dto.ViolationDTO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * ViolationMapper 통합 테스트
 *
 * - 실제 PostgreSQL (localhost:5432/aipass) 사용 — H2/인메모리 DB 사용 금지
 * - @Transactional: 각 테스트 종료 후 자동 롤백 → DB 상태 격리 보장
 * - violation_log 테이블의 violation_type 컬럼은 NOT NULL 이므로
 *   모든 insert 픽스처에 violationType 필드를 반드시 설정한다.
 */
@SpringBootTest
@Transactional
class ViolationMapperTest {

    @Autowired
    private ViolationMapper violationMapper;

    // -------------------------------------------------------------------------
    // 헬퍼 메서드
    // -------------------------------------------------------------------------

    /**
     * findAll / countAll 에 필요한 최소 파라미터 맵 생성.
     * size와 offset은 MyBatis SQL의 LIMIT/OFFSET에 직접 바인딩된다.
     */
    private Map<String, Object> buildParams(int size, int offset) {
        Map<String, Object> p = new HashMap<>();
        p.put("size", size);
        p.put("offset", offset);
        return p;
    }

    /**
     * 테스트용 ViolationDTO 픽스처를 생성한다.
     * eventId는 충돌 방지를 위해 호출마다 UUID를 포함한 고유값으로 설정한다.
     */
    private ViolationDTO buildDto(String plateNumber, String violationType) {
        ViolationDTO dto = new ViolationDTO();
        dto.setEventId("TEST-" + UUID.randomUUID());
        dto.setPlateNumber(plateNumber);
        dto.setViolationType(violationType);   // NOT NULL 컬럼
        dto.setImageUrl("http://example.com/img.jpg");
        dto.setSrcImageUrl("http://example.com/src.jpg");
        dto.setSpeedKmh(75.0);
        return dto;
    }

    // =========================================================================
    // insert
    // =========================================================================

    @Test
    @DisplayName("insert_NewViolation_SavesAllFields: 새 위반 삽입 후 모든 필드가 저장되어야 한다")
    void insert_NewViolation_SavesAllFields() {
        ViolationDTO dto = buildDto("12가3456", "과속");
        dto.setImageUrl("http://example.com/img_test.jpg");
        dto.setSrcImageUrl("http://example.com/src_test.jpg");
        dto.setSpeedKmh(95.5);

        violationMapper.insert(dto);

        // violation_id는 DB에서 생성되므로 findAll로 조회하여 결과 검증
        Map<String, Object> params = buildParams(100, 0);
        params.put("plateNumber", "12가3456");
        List<ViolationDTO> results = violationMapper.findAll(params);

        assertThat(results).isNotEmpty();
        ViolationDTO saved = results.stream()
                .filter(v -> dto.getEventId().equals(v.getEventId()))
                .findFirst()
                .orElseThrow(() -> new AssertionError("삽입된 레코드를 찾을 수 없음: " + dto.getEventId()));

        assertThat(saved.getPlateNumber()).isEqualTo("12가3456");
        assertThat(saved.getViolationType()).isEqualTo("과속");
        assertThat(saved.getImageUrl()).isEqualTo("http://example.com/img_test.jpg");
        assertThat(saved.getSrcImageUrl()).isEqualTo("http://example.com/src_test.jpg");
        assertThat(saved.getSpeedKmh()).isEqualTo(95.5);
        // 삽입 시 fine_status는 SQL에서 'UNPROCESSED'로 고정
        assertThat(saved.getFineStatus()).isEqualTo("UNPROCESSED");
    }

    @Test
    @DisplayName("insert_DuplicateEventId_Ignored: 동일 eventId 재삽입 시 ON CONFLICT DO NOTHING 으로 무시")
    void insert_DuplicateEventId_Ignored() {
        ViolationDTO dto = buildDto("99나9999", "신호위반");
        String sharedEventId = dto.getEventId(); // 두 번 모두 동일한 eventId 사용

        violationMapper.insert(dto);

        // 동일 eventId로 두 번째 삽입 시도
        ViolationDTO duplicate = new ViolationDTO();
        duplicate.setEventId(sharedEventId);
        duplicate.setPlateNumber("00다0000");   // 다른 번호판
        duplicate.setViolationType("과속");
        violationMapper.insert(duplicate);

        // 해당 eventId의 레코드 수는 여전히 1이어야 한다
        Map<String, Object> params = buildParams(100, 0);
        List<ViolationDTO> results = violationMapper.findAll(params);
        long countForEventId = results.stream()
                .filter(v -> sharedEventId.equals(v.getEventId()))
                .count();

        assertThat(countForEventId).isEqualTo(1);
    }

    // =========================================================================
    // findAll
    // =========================================================================

    @Test
    @DisplayName("findAll_ReturnsInsertedRecord: 삽입 후 findAll 결과에 해당 레코드가 포함되어야 한다")
    void findAll_ReturnsInsertedRecord() {
        ViolationDTO dto = buildDto("55마5555", "차선 위반");
        violationMapper.insert(dto);

        Map<String, Object> params = buildParams(100, 0);
        List<ViolationDTO> results = violationMapper.findAll(params);

        boolean found = results.stream()
                .anyMatch(v -> dto.getEventId().equals(v.getEventId()));
        assertThat(found).isTrue();
    }

    @Test
    @DisplayName("findAll_FilterByPlateNumber_FiltersCorrectly: 번호판 필터 적용 시 해당 번호판 레코드만 반환")
    void findAll_FilterByPlateNumber_FiltersCorrectly() {
        ViolationDTO dtoA = buildDto("11가1111", "과속");
        ViolationDTO dtoB = buildDto("22나2222", "신호위반");
        violationMapper.insert(dtoA);
        violationMapper.insert(dtoB);

        // "11가1111"로 필터링
        Map<String, Object> params = buildParams(100, 0);
        params.put("plateNumber", "11가1111");
        List<ViolationDTO> results = violationMapper.findAll(params);

        // 결과에 dtoA의 eventId가 포함되어야 함
        assertThat(results).anyMatch(v -> dtoA.getEventId().equals(v.getEventId()));
        // dtoB는 포함되어서는 안 됨
        assertThat(results).noneMatch(v -> dtoB.getEventId().equals(v.getEventId()));
    }

    @Test
    @DisplayName("findAll_FilterByFineStatus_FiltersCorrectly: fineStatus 필터 적용 시 해당 상태 레코드만 반환")
    void findAll_FilterByFineStatus_FiltersCorrectly() {
        ViolationDTO dto = buildDto("33바3333", "과속");
        violationMapper.insert(dto);

        // UNPROCESSED 필터: 삽입된 레코드가 포함되어야 함
        Map<String, Object> paramsUnprocessed = buildParams(100, 0);
        paramsUnprocessed.put("fineStatus", "UNPROCESSED");
        List<ViolationDTO> unprocessedResults = violationMapper.findAll(paramsUnprocessed);
        assertThat(unprocessedResults).anyMatch(v -> dto.getEventId().equals(v.getEventId()));

        // APPROVED 필터: 삽입된 레코드(UNPROCESSED)가 포함되어서는 안 됨
        Map<String, Object> paramsApproved = buildParams(100, 0);
        paramsApproved.put("fineStatus", "APPROVED");
        List<ViolationDTO> approvedResults = violationMapper.findAll(paramsApproved);
        assertThat(approvedResults).noneMatch(v -> dto.getEventId().equals(v.getEventId()));
    }

    // =========================================================================
    // countAll
    // =========================================================================

    @Test
    @DisplayName("countAll_ReturnsCorrectCount: N개 삽입 후 countAll이 정확한 수를 반환해야 한다")
    void countAll_ReturnsCorrectCount() {
        // 고유 번호판 접두사를 사용하여 다른 테스트 데이터와 격리
        String uniquePlate = "CNTTEST";
        int insertCount = 3;

        for (int i = 0; i < insertCount; i++) {
            ViolationDTO dto = new ViolationDTO();
            dto.setEventId("TEST-CNT-" + UUID.randomUUID());
            dto.setPlateNumber(uniquePlate + i);
            dto.setViolationType("과속");
            violationMapper.insert(dto);
        }

        // 각 레코드는 고유 번호판을 가지므로 ILIKE 검색으로 정확히 N개만 반환
        // "CNTTEST" prefix로 필터링하면 insertCount 개만 남음
        Map<String, Object> params = buildParams(100, 0);
        params.put("plateNumber", uniquePlate);
        int total = violationMapper.countAll(params);

        assertThat(total).isEqualTo(insertCount);
    }

    // =========================================================================
    // updateStatus
    // =========================================================================

    @Test
    @DisplayName("updateStatus_ChangesStatusCorrectly: updateStatus 호출 후 fine_status가 변경되어야 한다")
    void updateStatus_ChangesStatusCorrectly() {
        ViolationDTO dto = buildDto("44사4444", "신호위반");
        violationMapper.insert(dto);

        // 삽입된 레코드의 violation_id 조회
        Map<String, Object> params = buildParams(100, 0);
        params.put("plateNumber", "44사4444");
        List<ViolationDTO> inserted = violationMapper.findAll(params);
        ViolationDTO insertedDto = inserted.stream()
                .filter(v -> dto.getEventId().equals(v.getEventId()))
                .findFirst()
                .orElseThrow(() -> new AssertionError("삽입된 레코드를 찾을 수 없음"));

        Long id = insertedDto.getViolationId();

        // UNPROCESSED → APPROVED 로 상태 변경
        violationMapper.updateStatus(id, "APPROVED");

        ViolationDTO updated = violationMapper.findById(id);
        assertThat(updated).isNotNull();
        assertThat(updated.getFineStatus()).isEqualTo("APPROVED");
    }

    // =========================================================================
    // update (needs_review)
    // =========================================================================

    @Test
    @DisplayName("update_SetsNeedsReviewTrue: update 호출 후 needs_review=true, 번호판이 갱신되어야 한다")
    void update_SetsNeedsReviewTrue() {
        ViolationDTO dto = buildDto("66아6666", "과속");
        violationMapper.insert(dto);

        // violation_id 조회
        Map<String, Object> params = buildParams(100, 0);
        params.put("plateNumber", "66아6666");
        List<ViolationDTO> inserted = violationMapper.findAll(params);
        ViolationDTO insertedDto = inserted.stream()
                .filter(v -> dto.getEventId().equals(v.getEventId()))
                .findFirst()
                .orElseThrow(() -> new AssertionError("삽입된 레코드를 찾을 수 없음"));

        Long id = insertedDto.getViolationId();

        // 번호판 수정 요청 (update SQL은 needs_review = true 를 항상 설정)
        ViolationDTO updateDto = new ViolationDTO();
        updateDto.setViolationId(id);
        updateDto.setPlateNumber("77자7777");        // 수정된 번호판
        updateDto.setViolationType("신호위반");       // 수정된 위반유형
        updateDto.setFineStatus("UNPROCESSED");
        violationMapper.update(updateDto);

        ViolationDTO result = violationMapper.findById(id);
        assertThat(result).isNotNull();
        assertThat(result.getPlateNumber()).isEqualTo("77자7777");
        assertThat(result.getViolationType()).isEqualTo("신호위반");
        // violation.xml의 update SQL: needs_review = true 고정
        assertThat(result.getNeedsReview()).isTrue();
    }
}
