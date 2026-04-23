const FALLBACK = { label: '알수없음', color: '#9CA3AF', bg: 'rgba(156,163,175,0.15)' }

export function getRiskConfig(key) {
  return RISK_CONFIG[key] || FALLBACK
}

export function getStatusConfig(key) {
  return STATUS_CONFIG[key] || FALLBACK
}

export const RISK_CONFIG = {
  LOW:      { label: '정상', color: '#10B981', bg: 'rgba(16,185,129,0.15)' },
  MEDIUM:   { label: '주의', color: '#FBBF24', bg: 'rgba(251,191,36,0.15)' },
  HIGH:     { label: '경고', color: '#F59E0B', bg: 'rgba(245,158,11,0.15)' },
  CRITICAL: { label: '위험', color: '#EF4444', bg: 'rgba(239,68,68,0.15)' },
}

export const STATUS_CONFIG = {
  '정상가동': { label: '정상가동', color: '#10B981', bg: 'rgba(16,185,129,0.15)' },
  '점검요청': { label: '점검요청', color: '#FBBF24', bg: 'rgba(251,191,36,0.15)' },
  '점검중':   { label: '점검중',   color: '#1A6DCC', bg: 'rgba(26,109,204,0.15)' },
  '점검요망': { label: '점검요망', color: '#EF4444', bg: 'rgba(239,68,68,0.15)' },
  '통신오류': { label: '통신오류', color: '#9CA3AF', bg: 'rgba(156,163,175,0.15)' },
}

export const RUL_THRESHOLDS = {
  CRITICAL: 3,
  HIGH:     30,
  MEDIUM:   180,
}

export function formatRul(rul) {
  if (rul == null) return '-'
  if (rul <= RUL_THRESHOLDS.CRITICAL) return `${rul}일 이내`
  return `약 ${rul}일`
}

export function getRulColor(rul) {
  if (rul <= RUL_THRESHOLDS.CRITICAL) return '#EF4444'
  if (rul <= RUL_THRESHOLDS.HIGH)     return '#F59E0B'
  if (rul <= RUL_THRESHOLDS.MEDIUM)   return '#FBBF24'
  return '#10B981'
}

export const RISK_FILTER_OPTIONS = [
  { value: '', label: '위험도 전체' },
  { value: 'LOW', label: '정상' },
  { value: 'MEDIUM', label: '주의' },
  { value: 'HIGH', label: '경고' },
  { value: 'CRITICAL', label: '위험' },
]

export const STATUS_FILTER_OPTIONS = [
  { value: '', label: '상태 전체' },
  { value: '정상가동', label: '정상가동' },
  { value: '점검요청', label: '점검요청' },
  { value: '점검중',   label: '점검중' },
  { value: '점검요망', label: '점검요망' },
  { value: '통신오류', label: '통신오류' },
]
