import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, KeyRound, LoaderCircle, PlugZap, X } from 'lucide-react'
import { api } from '../api'

export function ProviderDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const client = useQueryClient()
  const state = useQuery({ queryKey: ['provider'], queryFn: api.provider })
  const contract = useQuery({ queryKey: ['contract'], queryFn: api.contract })
  const [key, setKey] = useState('')
  const [model, setModel] = useState('')
  const selectedModel = model || state.data?.model || contract.data?.imageModels[0] || ''
  const connect = useMutation({
    mutationFn: () => api.connect(key, selectedModel),
    onSuccess: (next) => { client.setQueryData(['provider'], next); setKey(''); setModel('') },
  })
  const disconnect = useMutation({
    mutationFn: api.disconnect,
    onSuccess: (next) => client.setQueryData(['provider'], next),
  })
  if (!open) return null
  const models = state.data?.models?.length ? state.data.models : contract.data?.imageModels || []
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="dialog provider-dialog" role="dialog" aria-modal="true" aria-labelledby="provider-title">
        <button className="icon-button dialog-close" onClick={onClose} aria-label="关闭"><X size={18} /></button>
        <div className="dialog-kicker"><PlugZap size={15} /> PROVIDER SESSION</div>
        <h2 id="provider-title">连接生成服务</h2>
        <p>凭据只保留在当前后端进程内存中，不进入浏览器存储、任务文件或 Git。</p>
        <div className={`connection-state ${state.data?.verified ? 'connected' : ''}`}>
          {state.data?.verified ? <Check size={17} /> : <KeyRound size={17} />}
          <span><b>{state.data?.verified ? '服务已连接' : '等待凭据'}</b><small>{state.data?.verified ? state.data.model : '也可输入 demo 体验完整流程'}</small></span>
        </div>
        <label className="field"><span>API KEY</span><input type="password" value={key} onChange={(event) => setKey(event.target.value)} placeholder="输入 Key，或使用 demo" autoComplete="off" /></label>
        <label className="field"><span>IMAGE MODEL</span><select value={selectedModel} onChange={(event) => setModel(event.target.value)}>{models.map((item) => <option key={item}>{item}</option>)}</select></label>
        {connect.error && <p className="form-error">{connect.error.message}</p>}
        <div className="dialog-actions">
          {state.data?.verified && <button className="button ghost" onClick={() => disconnect.mutate()}>断开</button>}
          <button className="button primary" disabled={!key || !selectedModel || connect.isPending} onClick={() => connect.mutate()}>
            {connect.isPending && <LoaderCircle className="spin" size={17} />}验证并连接
          </button>
        </div>
      </section>
    </div>
  )
}
