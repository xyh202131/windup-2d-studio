import { useState } from 'react'
import { Aperture, FolderOpen, Plus, Radio, Settings2 } from 'lucide-react'
import { Link, NavLink, Outlet } from 'react-router'
import { ProviderDialog } from './ProviderDialog'

export function StudioShell() {
  const [providerOpen, setProviderOpen] = useState(false)
  return (
    <div className="studio-shell">
      <aside className="rail">
        <Link className="brand" to="/" aria-label="Windup 2D 首页">
          <span className="brand-mark"><Aperture size={23} strokeWidth={1.5} /></span>
          <span><strong>WINDUP</strong><small>2D / HIGH DEFINITION</small></span>
        </Link>
        <nav className="rail-nav" aria-label="主导航">
          <NavLink to="/" end><FolderOpen size={18} /><span>资产灯箱</span></NavLink>
          <NavLink to="/create"><Plus size={18} /><span>创建人物</span></NavLink>
        </nav>
        <div className="rail-note">
          <Radio size={16} />
          <span><b>LOCAL STUDIO</b><small>候选优先 · 安全入库</small></span>
        </div>
        <button className="provider-trigger" onClick={() => setProviderOpen(true)}>
          <Settings2 size={17} /><span>生成服务</span>
        </button>
      </aside>
      <main className="studio-main">
        <Outlet />
      </main>
      <ProviderDialog open={providerOpen} onClose={() => setProviderOpen(false)} />
    </div>
  )
}
