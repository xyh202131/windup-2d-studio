import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, ChevronLeft, ChevronRight, CircleAlert, LoaderCircle, Pause, Play, RefreshCw, ShieldCheck, X } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { api } from '../api'
import { StatusPill } from '../components/StatusPill'
import { useJob } from '../query'
import type { OutputSlot } from '../types'

function selectedVersion(output: OutputSlot | undefined) {
  return output?.versions.find((item) => item.id === output.selectedVersionId)
}

export function JobPage() {
  const { jobId = '' } = useParams()
  const client = useQueryClient()
  const job = useJob(jobId)
  const [slotId, setSlotId] = useState('')
  const [playing, setPlaying] = useState(false)
  const [revision, setRevision] = useState('')
  const [frameCursor, setFrameCursor] = useState(0)
  const outputs = useMemo(() => Object.values(job.data?.outputs || {}).sort((a, b) => (a.index ?? 0) - (b.index ?? 0)), [job.data?.outputs])
  const frameOutputs = outputs.filter((item) => item.kind === 'frame')
  useEffect(() => {
    if (!playing || !frameOutputs.length) return
    const timer = window.setInterval(() => setFrameCursor((value) => (value + 1) % frameOutputs.length), 125)
    return () => window.clearInterval(timer)
  }, [frameOutputs.length, playing])
  const effectiveSlotId = playing && frameOutputs[frameCursor]
    ? frameOutputs[frameCursor].slot
    : slotId || outputs[0]?.slot || ''
  const refresh = () => client.invalidateQueries({ queryKey: ['job', jobId] })
  const review = useMutation({ mutationFn: ({ slot, decision }: { slot: string; decision: 'approved' | 'rejected' }) => api.review(jobId, slot, decision), onSuccess: (next) => client.setQueryData(['job', jobId], next) })
  const regenerate = useMutation({ mutationFn: () => api.regenerate(jobId, effectiveSlotId, revision), onSuccess: (next) => { client.setQueryData(['job', jobId], next); setRevision('') } })
  const select = useMutation({ mutationFn: (versionId: string) => api.select(jobId, effectiveSlotId, versionId), onSuccess: (next) => client.setQueryData(['job', jobId], next) })
  const promote = useMutation({ mutationFn: () => api.promote(jobId), onSuccess: (next) => { client.setQueryData(['job', jobId], next); client.invalidateQueries({ queryKey: ['characters'] }); client.invalidateQueries({ queryKey: ['character', next.characterId] }) } })
  const retry = useMutation({ mutationFn: () => api.retry(jobId), onSuccess: (next) => client.setQueryData(['job', jobId], next) })
  const selected = job.data?.outputs[effectiveSlotId]
  const version = selectedVersion(selected)
  const allApproved = outputs.length > 0 && outputs.every((item) => item.review.decision === 'approved')
  if (job.isLoading || !job.data) return <div className="page loading-page">正在打开候选灯箱…</div>
  const data = job.data
  const active = ['queued', 'planning', 'generating', 'processing', 'promoting'].includes(data.status)
  return (
    <div className="review-page">
      <header className="review-topbar">
        <Link className="back-link" to={data.status === 'approved' ? `/characters/${data.characterId}` : '/'}><ArrowLeft size={17} />{data.status === 'approved' ? '角色详情' : '资产灯箱'}</Link>
        <div className="job-title"><span>{data.type === 'character' ? 'IDENTITY MASTER' : 'MOTION SEQUENCE'}</span><b>{data.type === 'character' ? '三视角母版审核' : `${String(data.payload.action)} · ${String(data.payload.frameCount)} 帧`}</b></div>
        <StatusPill status={data.status} />
      </header>
      <div className="review-workspace">
        <aside className="filmstrip-panel">
          <header><span>OUTPUTS</span><b>{outputs.length.toString().padStart(2, '0')}</b></header>
          <div className="filmstrip-list">
            {outputs.map((output) => {
              const image = selectedVersion(output)
              return <button key={output.slot} className={`${effectiveSlotId === output.slot ? 'selected' : ''} review-${output.review.decision}`} onClick={() => { setSlotId(output.slot); setPlaying(false) }}>
                <span className="frame-number">{output.kind === 'frame' ? String((output.index ?? 0) + 1).padStart(2, '0') : output.label.slice(0, 1)}</span>
                {image && <img src={image.url} alt={output.label} />}
                <i>{output.review.decision === 'approved' ? <Check size={12} /> : output.review.decision === 'rejected' ? <X size={12} /> : null}</i>
              </button>
            })}
          </div>
        </aside>
        <main className="review-canvas">
          <div className="canvas-meta"><span>{selected?.label || '等待输出'}</span><small>{version ? `${version.width} × ${version.height} / ${version.label}` : 'GENERATION IN PROGRESS'}</small></div>
          <div className="canvas-stage">
            <div className="canvas-grid" />
            {version ? <img src={version.url} alt={selected?.label} /> : <div className="generation-orbit"><LoaderCircle size={42} /><span>{data.message}</span></div>}
            <div className="ground-guide"><span>GROUND 90%</span></div>
          </div>
          {frameOutputs.length > 0 && <div className="playback-controls"><button onClick={() => setFrameCursor((frameCursor - 1 + frameOutputs.length) % frameOutputs.length)}><ChevronLeft /></button><button className="play-toggle" onClick={() => setPlaying(!playing)}>{playing ? <Pause /> : <Play />}</button><button onClick={() => setFrameCursor((frameCursor + 1) % frameOutputs.length)}><ChevronRight /></button><span>8 FPS · {frameCursor + 1}/{frameOutputs.length}</span></div>}
          {active && <div className="generation-progress"><div><i style={{ width: `${data.progress}%` }} /></div><span><b>{data.progress}%</b>{data.message}</span></div>}
        </main>
        <aside className="inspector-panel">
          <section><span className="eyebrow">QUALITY INSPECTOR</span><h2>{selected?.label || '候选检查'}</h2></section>
          {version && <>
            <section className="inspection-stats"><div><span>画布</span><b>{version.width}px</b></div><div><span>主体占比</span><b>{Math.round((version.quality.coverage || 0) * 100)}%</b></div><div><span>脚底线</span><b>{version.quality.footY}px</b></div></section>
            <section className="quality-report">
              {version.quality.warnings?.length ? version.quality.warnings.map((warning) => <p key={warning}><CircleAlert size={15} />{warning}</p>) : <p className="quality-ok"><ShieldCheck size={16} />基础几何检查通过</p>}
              {data.payload.sequenceQuality?.warnings?.map((warning) => <p key={warning}><CircleAlert size={15} />{warning}</p>)}
              <small>自动检查无法判断解剖、变脸与动作语义，请人工确认。</small>
            </section>
            <section className="version-section"><header><span>候选版本</span><b>{selected?.versions.length}</b></header><div>{selected?.versions.map((item) => <button className={item.id === selected.selectedVersionId ? 'selected' : ''} key={item.id} onClick={() => select.mutate(item.id)}><img src={item.url} alt={item.label} /><span>{item.label}</span></button>)}</div></section>
            {data.status === 'awaiting_review' && <section className="review-actions"><button className="button approve" onClick={() => review.mutate({ slot: effectiveSlotId, decision: 'approved' })}><Check size={17} />通过</button><button className="button reject" onClick={() => review.mutate({ slot: effectiveSlotId, decision: 'rejected' })}><X size={17} />退回</button></section>}
            {data.status === 'awaiting_review' && <section className="revision-box"><label className="field"><span>局部重生要求</span><textarea value={revision} onChange={(event) => setRevision(event.target.value)} placeholder="指出需要修复的身份、服装或姿势问题…" /></label><button className="button ghost" disabled={regenerate.isPending} onClick={() => regenerate.mutate()}><RefreshCw size={16} />生成新变体</button></section>}
          </>}
          {data.error && <p className="form-error">{data.error}</p>}
          {['failed', 'interrupted'].includes(data.status) && <button className="button primary full-button" disabled={retry.isPending} onClick={() => retry.mutate()}><RefreshCw size={17} />重新执行任务</button>}
          {data.status === 'awaiting_review' && <button className="button primary full-button" disabled={!allApproved || promote.isPending} onClick={() => promote.mutate()}>{promote.isPending && <LoaderCircle className="spin" size={17} />}全部通过并正式入库</button>}
          {data.status === 'approved' && <Link className="button primary full-button" to={`/characters/${data.characterId}`}>查看正式角色资产</Link>}
          <button className="refresh-link" onClick={refresh}>刷新任务状态</button>
        </aside>
      </div>
    </div>
  )
}
