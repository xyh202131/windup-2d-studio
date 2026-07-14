import type { JobStatus } from '../types'

const labels: Record<JobStatus, string> = {
  queued: '排队中', planning: '动作规划', generating: '生成中', processing: '处理中', awaiting_review: '等待审核',
  promoting: '入库中', approved: '已入库', failed: '失败', interrupted: '已中断', cancelled: '已取消',
}

export function StatusPill({ status }: { status: JobStatus }) {
  return <span className={`status-pill status-${status}`}><i />{labels[status]}</span>
}
