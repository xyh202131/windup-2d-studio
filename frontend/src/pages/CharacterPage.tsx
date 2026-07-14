import { FormEvent, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, Box, Download, Film, LoaderCircle, Play, Sparkles } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router'
import { api } from '../api'
import type { ViewId } from '../types'

export function CharacterPage() {
  const { characterId = '' } = useParams()
  const navigate = useNavigate()
  const character = useQuery({ queryKey: ['character', characterId], queryFn: () => api.character(characterId) })
  const contract = useQuery({ queryKey: ['contract'], queryFn: api.contract })
  const provider = useQuery({ queryKey: ['provider'], queryFn: api.provider })
  const [view, setView] = useState<ViewId>('side')
  const [action, setAction] = useState('idle')
  const [customAction, setCustomAction] = useState('')
  const [frameCount, setFrameCount] = useState<8 | 12 | 16>(8)
  const [loop, setLoop] = useState(true)
  const [prompt, setPrompt] = useState('')
  const create = useMutation({
    mutationFn: (payload: object) => api.createAction(characterId, payload),
    onSuccess: (job) => navigate(`/jobs/${job.id}`),
  })
  if (character.isLoading) return <div className="page loading-page">正在读取角色资产…</div>
  if (!character.data) return <div className="page loading-page">角色不存在</div>
  const item = character.data
  const isCustom = action === 'custom'
  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate({
      action: isCustom ? (customAction.trim() || 'custom') : action,
      description: isCustom ? customAction : contract.data?.actions[action]?.label || action,
      view, frameCount, loop, customPrompt: prompt,
    })
  }
  return (
    <div className="page character-page">
      <header className="page-header character-header">
        <div><Link className="back-link" to="/"><ArrowLeft size={17} />资产灯箱</Link><span className="eyebrow">CHARACTER DOSSIER / {item.id.slice(-4).toUpperCase()}</span><h1>{item.name}</h1><p>{item.description}</p></div>
        <a className="button ghost" href={`/api/v1/characters/${item.id}/export`}><Download size={17} />导出资产包</a>
      </header>
      <section className="master-lightbox">
        {(Object.keys(contract.data?.views || {}) as ViewId[]).map((id) => <article key={id} className="master-card">
          <header><span>{contract.data?.views[id].label}</span><i>{item.masters[id] ? 'APPROVED' : 'MISSING'}</i></header>
          <div>{item.masters[id] ? <img src={item.masters[id]} alt={`${item.name}${contract.data?.views[id].label}母版`} /> : <Box size={42} />}</div>
          <small>1024 × 1024 / TRANSPARENT</small>
        </article>)}
      </section>
      <section className="character-lower-grid">
        <form className="panel action-builder" onSubmit={submit}>
          <header className="panel-header"><div><span className="eyebrow">ACTION BUILDER</span><h2>生成动作序列</h2></div><Sparkles size={20} /></header>
          <div className="action-form-grid">
            <label className="field"><span>真实视角</span><select value={view} onChange={(event) => setView(event.target.value as ViewId)}>{Object.entries(contract.data?.views || {}).map(([id, value]) => <option value={id} key={id}>{value.label}</option>)}</select></label>
            <label className="field"><span>动作</span><select value={action} onChange={(event) => { const next = event.target.value; setAction(next); setLoop(next === 'custom' ? loop : Boolean(contract.data?.actions[next]?.loop)) }}>{Object.entries(contract.data?.actions || {}).map(([id, value]) => <option value={id} key={id}>{value.label}</option>)}<option value="custom">自定义动作…</option></select></label>
            <label className="field"><span>帧数</span><select value={frameCount} onChange={(event) => setFrameCount(Number(event.target.value) as 8 | 12 | 16)}>{contract.data?.frameCounts.map((count) => <option key={count} value={count}>{count} 帧</option>)}</select></label>
            <label className="toggle-field"><input type="checkbox" checked={loop} onChange={(event) => setLoop(event.target.checked)} /><span><b>循环动作</b><small>检查首尾接缝</small></span></label>
          </div>
          {isCustom && <label className="field"><span>自定义动作描述</span><input required value={customAction} onChange={(event) => setCustomAction(event.target.value)} placeholder="例如：拔剑后向前完成一次横斩并收势" /></label>}
          <label className="field"><span>附加动作约束 · 可选</span><textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="例如：围巾运动幅度小，武器始终握在右手…" /></label>
          <div className="anchor-strip">{['01', '02', '03', '04'].map((number, index) => <div key={number}><i>{number}</i><span>{['准备', '关键姿势', '主要冲击', '恢复'][index]}</span></div>)}</div>
          {create.error && <p className="form-error">{create.error.message}</p>}
          <button className="button primary" disabled={!provider.data?.verified || create.isPending || item.status !== 'approved'}>{create.isPending && <LoaderCircle className="spin" size={17} />}生成 {frameCount} 帧高清动作</button>
        </form>
        <aside className="panel action-library">
          <header className="panel-header"><div><span className="eyebrow">PUBLISHED MOTION</span><h2>正式动作</h2></div><span>{item.actions.length}</span></header>
          {item.actions.length ? item.actions.map((motion) => <Link to={`/jobs/${motion.jobId}`} className="motion-row" key={motion.jobId}><div><Play size={16} /></div><span><b>{contract.data?.actions[motion.action]?.label || motion.action}</b><small>{contract.data?.views[motion.view]?.label} · {motion.frameCount} 帧</small></span><Film size={17} /></Link>) : <div className="empty-state compact"><Film size={25} /><b>尚无正式动作</b><span>从左侧生成第一组动作序列。</span></div>}
        </aside>
      </section>
    </div>
  )
}

