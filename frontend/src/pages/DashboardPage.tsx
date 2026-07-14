import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Box, Film, ImagePlus, Layers3, Sparkles } from 'lucide-react'
import { Link } from 'react-router'
import { api } from '../api'
import { StatusPill } from '../components/StatusPill'

export function DashboardPage() {
  const characters = useQuery({ queryKey: ['characters'], queryFn: api.characters })
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: () => api.jobs() })
  const provider = useQuery({ queryKey: ['provider'], queryFn: api.provider })
  const items = characters.data?.items || []
  const recentJobs = (jobs.data?.items || []).slice(0, 5)
  return (
    <div className="page dashboard-page">
      <header className="page-header dashboard-header">
        <div><span className="eyebrow">CHARACTER ASSET LIGHTBOX / 01</span><h1>把人物画出来，<em>让动作活起来。</em></h1></div>
        <div className={`live-chip ${provider.data?.verified ? 'online' : ''}`}><i />{provider.data?.verified ? '生成服务在线' : '生成服务未连接'}</div>
      </header>

      <section className="hero-lightbox">
        <div className="hero-copy">
          <span className="section-number">HD—2D</span>
          <p>1024 母版</p><p>512 动作帧</p><p>三视角身份锁定</p>
          <Link className="button primary hero-button" to="/create"><ImagePlus size={18} />创建高清人物<ArrowRight size={17} /></Link>
        </div>
        <div className="hero-figure" aria-hidden="true">
          <div className="scan-line" />
          <div className="figure-head" /><div className="figure-body" /><div className="figure-leg left" /><div className="figure-leg right" />
          <span>IDENTITY MASTER</span>
        </div>
        <div className="hero-specs">
          <div><Sparkles size={18} /><span><b>原生高清</b><small>拒绝低清放大</small></span></div>
          <div><Layers3 size={18} /><span><b>候选隔离</b><small>审核后才入库</small></span></div>
          <div><Film size={18} /><span><b>逐帧版本</b><small>坏帧局部重生</small></span></div>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="panel asset-panel">
          <header className="panel-header"><div><span className="eyebrow">ASSET LIBRARY</span><h2>人物资产</h2></div><span>{items.length.toString().padStart(2, '0')}</span></header>
          {characters.isLoading ? <div className="empty-state">正在点亮资产灯箱…</div> : items.length ? (
            <div className="character-grid">
              {items.map((character) => {
                const portrait = character.masters.three_quarter || character.masters.front || character.masters.side
                return <Link className="character-card" key={character.id} to={`/characters/${character.id}`}>
                  <div className="character-portrait">{portrait ? <img src={portrait} alt={character.name} /> : <Box size={42} />}</div>
                  <div><span className={`asset-state ${character.status}`}>{character.status === 'approved' ? '正式资产' : '生成中'}</span><h3>{character.name}</h3><p>{character.description}</p></div>
                  <ArrowRight size={18} />
                </Link>
              })}
            </div>
          ) : <div className="empty-state"><Box size={28} /><b>还没有人物资产</b><span>创建第一位角色，三视角母版会在这里汇合。</span></div>}
        </div>
        <aside className="panel activity-panel">
          <header className="panel-header"><div><span className="eyebrow">LIVE QUEUE</span><h2>最近任务</h2></div></header>
          <div className="job-list">
            {recentJobs.map((job) => <Link key={job.id} to={`/jobs/${job.id}`} className="job-row">
              <div className="job-type">{job.type === 'character' ? 'M' : 'A'}</div>
              <div><b>{job.type === 'character' ? '人物母版' : String(job.payload.action || '动作序列')}</b><small>{job.message}</small></div>
              <StatusPill status={job.status} />
            </Link>)}
            {!recentJobs.length && <div className="empty-state compact">暂无任务记录</div>}
          </div>
        </aside>
      </section>
    </div>
  )
}

