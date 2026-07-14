import { FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, FileImage, LoaderCircle, ShieldCheck, UploadCloud } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { api } from '../api'
import type { StyleId } from '../types'

const samples = [
  { name: '雾港巡灯者', description: '年轻的港城巡灯者，清瘦挺拔，黑色短发，穿深海军蓝长外套和旧铜扣，携带一盏小型黄铜风灯，气质安静坚定。', style: 'hand_drawn' as StyleId },
  { name: '赤羽剑士', description: '二十岁左右的东方女剑士，赤褐长发高束，轻型黑红护甲，腰间佩细长刀，动作敏捷，神情锐利但克制。', style: 'anime' as StyleId },
  { name: '荒原信使', description: '历经风沙的年轻信使，浅棕短发与护目镜，穿磨损皮夹克、围巾和长靴，背轻型邮包，身形矫健。', style: 'semi_realistic' as StyleId },
]

export function CreateCharacterPage() {
  const navigate = useNavigate()
  const contract = useQuery({ queryKey: ['contract'], queryFn: api.contract })
  const provider = useQuery({ queryKey: ['provider'], queryFn: api.provider })
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [style, setStyle] = useState<StyleId>('hand_drawn')
  const [customStyle, setCustomStyle] = useState('')
  const [reference, setReference] = useState<File | null>(null)
  const preview = useMemo(() => reference ? URL.createObjectURL(reference) : '', [reference])
  const create = useMutation({
    mutationFn: (form: FormData) => api.createCharacter(form),
    onSuccess: (job) => navigate(`/jobs/${job.id}`),
  })
  function submit(event: FormEvent) {
    event.preventDefault()
    const form = new FormData()
    form.set('name', name); form.set('description', description); form.set('style', style); form.set('customStyle', customStyle)
    if (reference) form.set('reference', reference)
    create.mutate(form)
  }
  return (
    <div className="page create-page">
      <header className="page-header compact-header">
        <Link className="back-link" to="/"><ArrowLeft size={17} />返回资产灯箱</Link>
        <div><span className="eyebrow">NEW IDENTITY / 02</span><h1>建立人物身份母版</h1><p>一次生成侧视、正面与 3/4 三个真实视角，审核后再进入动作生产。</p></div>
      </header>
      <form className="creation-workbench" onSubmit={submit}>
        <section className="panel definition-panel">
          <header className="panel-header"><div><span className="step-index">01</span><h2>人物定义</h2></div><small>IDENTITY BRIEF</small></header>
          <div className="sample-row">{samples.map((sample) => <button type="button" key={sample.name} onClick={() => { setName(sample.name); setDescription(sample.description); setStyle(sample.style) }}>{sample.name}</button>)}</div>
          <label className="field"><span>资产名称</span><input required maxLength={80} value={name} onChange={(event) => setName(event.target.value)} placeholder="给角色一个可识别的名字" /></label>
          <label className="field"><span>身份描述</span><textarea required minLength={8} maxLength={1600} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="年龄、身形、五官、发型、服装结构、道具和气质…" /></label>
          <div className="field"><span>美术方向</span><div className="style-options">{Object.entries(contract.data?.styles || {}).map(([id, item]) => <button className={style === id ? 'selected' : ''} type="button" key={id} onClick={() => setStyle(id as StyleId)}><b>{item.label}</b><small>{id === 'hand_drawn' ? '细腻笔触' : id === 'anime' ? '清晰色块' : '真实材质'}</small></button>)}</div></div>
          <label className="field"><span>附加风格约束 · 可选</span><input maxLength={500} value={customStyle} onChange={(event) => setCustomStyle(event.target.value)} placeholder="例如：低饱和、无描边、东方幻想服饰" /></label>
        </section>
        <section className="panel reference-panel">
          <header className="panel-header"><div><span className="step-index">02</span><h2>身份参考</h2></div><small>OPTIONAL</small></header>
          <label className={`upload-zone ${preview ? 'has-preview' : ''}`}>
            {preview ? <img src={preview} alt="参考图预览" /> : <><UploadCloud size={32} /><b>拖入或选择参考图</b><span>PNG / JPEG / WebP · 最高 15MB</span></>}
            <input hidden type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => setReference(event.target.files?.[0] || null)} />
          </label>
          {reference && <div className="file-chip"><FileImage size={17} /><span><b>{reference.name}</b><small>{(reference.size / 1024 / 1024).toFixed(2)} MB</small></span><button type="button" onClick={() => setReference(null)}>移除</button></div>}
          <div className="output-contract">
            <span>OUTPUT CONTRACT</span>
            <div><b>3</b><small>真实视角</small></div><div><b>1024</b><small>母版像素</small></div><div><b>α</b><small>透明背景</small></div>
          </div>
          <div className="security-line"><ShieldCheck size={17} /><span>参考图只写入本机运行目录，不会提交到 Git。</span></div>
          {create.error && <p className="form-error">{create.error.message}</p>}
          <button className="button primary create-submit" type="submit" disabled={!provider.data?.verified || create.isPending || !name || description.length < 8}>
            {create.isPending ? <LoaderCircle className="spin" size={18} /> : <ArrowRight size={18} />}
            {provider.data?.verified ? '生成三视角母版' : '请先连接生成服务'}
          </button>
        </section>
      </form>
    </div>
  )
}
