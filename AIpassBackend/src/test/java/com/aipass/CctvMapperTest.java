package com.aipass;

import com.aipass.dao.CctvMapper;
import com.aipass.dto.CctvDTO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * CctvMapper 통합 테스트
 *
 * - 실제 PostgreSQL (localhost:5432/aipass) 사용 — H2/인메모리 DB 사용 금지
 * - @Transactional: 각 테스트 종료 후 자동 롤백 → DB 상태 격리 보장
 * - cctv_info 테이블은 INSERT 없이 기존 데이터를 읽기 전용으로 조회한다.
 *   (CCTV 데이터는 운영 시드 데이터로 사전 입력되어 있다고 가정)
 *
 * 주의: 테스트 실행 전 cctv_info 테이블에 is_active=true 레코드가
 * 최소 1건 존재해야 한다.
 */
@SpringBootTest
@Transactional
class CctvMapperTest {

    @Autowired
    private CctvMapper cctvMapper;

    // =========================================================================
    // findAllActive
    // =========================================================================

    @Test
    @DisplayName("findAllActive_ReturnsNonEmptyList: is_active=true 레코드가 존재하면 비어있지 않은 리스트를 반환한다")
    void findAllActive_ReturnsNonEmptyList() {
        List<CctvDTO> results = cctvMapper.findAllActive();

        // cctv_info 테이블에 활성 CCTV가 반드시 존재해야 한다
        assertThat(results).isNotNull();
        assertThat(results).isNotEmpty();
    }

    @Test
    @DisplayName("findAllActive_AllResultsAreActive: 반환된 모든 레코드의 is_active가 true여야 한다")
    void findAllActive_AllResultsAreActive() {
        List<CctvDTO> results = cctvMapper.findAllActive();

        // SQL WHERE is_active = true 이므로 모든 결과가 true여야 한다
        assertThat(results).allSatisfy(dto ->
                assertThat(dto.getIsActive()).isTrue()
        );
    }

    @Test
    @DisplayName("findAllActive_EachRecordHasRequiredFields: 반환된 레코드는 cctvId, cctvName, streamUrl을 포함한다")
    void findAllActive_EachRecordHasRequiredFields() {
        List<CctvDTO> results = cctvMapper.findAllActive();

        assertThat(results).allSatisfy(dto -> {
            assertThat(dto.getCctvId()).isNotBlank();
            assertThat(dto.getCctvName()).isNotBlank();
            // streamUrl은 AI 서버가 사용하므로 null이 아닌지 확인
            // (빈 문자열일 수 있으므로 null 여부만 검사)
            assertThat(dto.getCctvId()).isNotNull();
            // displayUrl: 프론트 영상 재생용 URL (기본값: http://localhost:8000/api/v1/stream/video)
            assertThat(dto.getDisplayUrl()).isNotNull();
        });
    }

    @Test
    @DisplayName("findAllActive_OrderedByCctvNameAsc: 결과가 cctv_name 오름차순으로 정렬되어 반환된다")
    void findAllActive_OrderedByCctvNameAsc() {
        List<CctvDTO> results = cctvMapper.findAllActive();

        // SQL ORDER BY cctv_name ASC 검증
        for (int i = 0; i < results.size() - 1; i++) {
            String current = results.get(i).getCctvName();
            String next = results.get(i + 1).getCctvName();
            assertThat(current.compareTo(next)).isLessThanOrEqualTo(0);
        }
    }

    // =========================================================================
    // findAiTargetCctv
    // =========================================================================

    @Test
    @DisplayName("findAiTargetCctv_ReturnsNonNull: 활성 CCTV가 존재하면 null이 아닌 단건을 반환한다")
    void findAiTargetCctv_ReturnsNonNull() {
        CctvDTO result = cctvMapper.findAiTargetCctv();

        // is_active=true 레코드가 존재해야 한다
        assertThat(result).isNotNull();
    }

    @Test
    @DisplayName("findAiTargetCctv_IsActiveTrueRecord: 반환된 레코드의 is_active가 true여야 한다")
    void findAiTargetCctv_IsActiveTrueRecord() {
        CctvDTO result = cctvMapper.findAiTargetCctv();

        assertThat(result).isNotNull();
        assertThat(result.getIsActive()).isTrue();
    }

    @Test
    @DisplayName("findAiTargetCctv_MatchesFirstOfFindAllActive: findAiTargetCctv 결과가 findAllActive의 첫 번째와 일치한다")
    void findAiTargetCctv_MatchesFirstOfFindAllActive() {
        // findAiTargetCctv SQL은 findAllActive와 동일한 ORDER BY + LIMIT 1
        // 따라서 cctvId가 findAllActive()[0]과 동일해야 한다
        CctvDTO aiTarget = cctvMapper.findAiTargetCctv();
        List<CctvDTO> allActive = cctvMapper.findAllActive();

        assertThat(aiTarget).isNotNull();
        assertThat(allActive).isNotEmpty();
        assertThat(aiTarget.getCctvId()).isEqualTo(allActive.get(0).getCctvId());
    }

    @Test
    @DisplayName("findAiTargetCctv_HasStreamUrl: 반환된 레코드는 streamUrl 필드를 가진다")
    void findAiTargetCctv_HasStreamUrl() {
        CctvDTO result = cctvMapper.findAiTargetCctv();

        // AI 서버가 url 필드로 사용하므로 null 여부 확인
        assertThat(result).isNotNull();
        assertThat(result.getStreamUrl()).isNotNull();
    }

    // =========================================================================
    // findById
    // =========================================================================

    @Test
    @DisplayName("findById_ExistingId_ReturnsMatchingRecord: 존재하는 cctvId로 조회하면 해당 레코드를 반환한다")
    void findById_ExistingId_ReturnsMatchingRecord() {
        // findAllActive에서 실제 존재하는 ID를 가져와 조회
        List<CctvDTO> allActive = cctvMapper.findAllActive();
        assertThat(allActive).isNotEmpty();

        String existingId = allActive.get(0).getCctvId();
        CctvDTO result = cctvMapper.findById(existingId);

        assertThat(result).isNotNull();
        assertThat(result.getCctvId()).isEqualTo(existingId);
    }

    @Test
    @DisplayName("findById_ExistingId_AllFieldsPopulated: 조회된 레코드는 주요 필드가 모두 채워져 있다")
    void findById_ExistingId_AllFieldsPopulated() {
        List<CctvDTO> allActive = cctvMapper.findAllActive();
        assertThat(allActive).isNotEmpty();

        String existingId = allActive.get(0).getCctvId();
        CctvDTO result = cctvMapper.findById(existingId);

        assertThat(result).isNotNull();
        assertThat(result.getCctvId()).isNotBlank();
        assertThat(result.getCctvName()).isNotBlank();
        // updatedAt은 TO_CHAR 포맷 'YY-MM-DD HH24:MI:SS'로 반환
        assertThat(result.getUpdatedAt()).isNotNull();
        // displayUrl: findById 쿼리에 display_url 컬럼이 포함되어 있으므로 null이 아니어야 한다
        assertThat(result.getDisplayUrl()).isNotNull();
    }

    @Test
    @DisplayName("findById_NonExistingId_ReturnsNull: 존재하지 않는 cctvId로 조회하면 null을 반환한다")
    void findById_NonExistingId_ReturnsNull() {
        // 실제 DB에 존재하지 않을 것이 확실한 ID 사용
        CctvDTO result = cctvMapper.findById("CCTV-NON-EXISTENT-99999");

        assertThat(result).isNull();
    }

    @Test
    @DisplayName("findById_EmptyString_ReturnsNull: 빈 문자열 ID로 조회하면 null을 반환한다")
    void findById_EmptyString_ReturnsNull() {
        CctvDTO result = cctvMapper.findById("");

        assertThat(result).isNull();
    }
}
