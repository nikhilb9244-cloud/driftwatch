import { renderTool } from './workspace-tools';
import { scene, mountScene } from './workspace-globe';

export const $ = <T extends HTMLElement = HTMLElement>(id: string): T => document.getElementById(id) as T;
export const esc = (v: unknown): string => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
export const num = (v: unknown, digits = 2): string => typeof v === 'number' && Number.isFinite(v) ? v.toLocaleString('en-GB', {maximumFractionDigits: digits}) : '—';
export function download(name: string, value: unknown, type = 'application/json'): void {
  const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  const blob = new Blob([text], {type});
  const url = URL.createObjectURL(blob);
  const dialog = document.createElement('dialog');
  dialog.className = 'export-dialog';
  dialog.setAttribute('aria-labelledby','export-title');
  dialog.innerHTML = `<div class="dialog-head"><h2 id="export-title">Your export is ready.</h2><button class="icon-button" aria-label="Close export">×</button></div><p class="export-filename"></p><p class="card-sub">Review the contents, then download the file or copy the full text. This export stays on your computer.</p><label class="field">Report preview<textarea readonly spellcheck="false"></textarea><small></small></label><div class="export-actions"><a class="primary" download>Download file ↓</a><button class="secondary copy-export" type="button">Copy full text</button><button class="secondary select-export" type="button">Select full text</button></div><p class="status-line" role="status">No file has been saved yet.</p>`;
  dialog.querySelector('.export-filename')!.textContent = `${name} · ${num(blob.size / 1024,1)} KB`;
  const preview = dialog.querySelector('textarea')!;
  preview.value = text.slice(0,60000);
  dialog.querySelector('small')!.textContent = text.length > 60000 ? 'Preview limited to 60,000 characters. Download and copy include the complete file.' : 'Complete file shown. No source data has been changed.';
  const link = dialog.querySelector('a')!; link.href = url; link.download = name;
  const status = dialog.querySelector('[role=status]')!;
  link.onclick = () => { status.textContent = 'Download requested. Check your browser’s downloads; if it does not save, use Copy full text.'; };
  const selectFullText = () => {
    preview.value = text;
    dialog.querySelector('small')!.textContent = 'Complete file shown. No source data has been changed.';
    preview.focus(); preview.select();
  };
  dialog.querySelector<HTMLButtonElement>('.select-export')!.onclick = () => {
    selectFullText(); status.textContent = 'Full export selected. Press Ctrl+C (or ⌘C), then paste into a local text editor and save it with the filename above.';
  };
  dialog.querySelector<HTMLButtonElement>('.copy-export')!.onclick = async () => {
    try { await navigator.clipboard.writeText(text); status.textContent = 'Full export copied. Paste it into a local text editor and save it with the filename above.'; }
    catch { selectFullText(); status.textContent = 'Automatic clipboard access is unavailable. The full export is selected: press Ctrl+C (or ⌘C), then paste into a local text editor and save it with the filename above.'; }
  };
  dialog.querySelector<HTMLButtonElement>('.icon-button')!.onclick = () => dialog.close();
  dialog.addEventListener('close', () => { dialog.remove(); setTimeout(() => URL.revokeObjectURL(url),60000); }, {once:true});
  document.body.append(dialog); dialog.showModal();
}
export const metric = (label: string, value: string, note: string, tone = '') => `<div class="metric"><div class="metric-label">${label}</div><div class="metric-value ${tone}">${value}</div><p class="metric-note">${note}</p></div>`;
export const header = (eyebrow: string, title: string, intro: string, actions = '') => `<div class="page-head"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="intro">${intro}</p></div>${actions ? `<div class="head-actions">${actions}</div>` : ''}</div>`;
export interface Series {label: string; colour: string; values: [number, number | null][]; dashed?: boolean}
export function chart(series: Series[], xLabel: string, yLabel: string): string {
  const values = series.flatMap(s => s.values.filter((p): p is [number, number] => Number.isFinite(p[0]) && p[1] !== null && Number.isFinite(p[1])));
  if (!values.length) return '<div class="empty">No usable measurements to plot.</div>';
  const xMin = Math.min(...values.map(v => v[0])), xMax = Math.max(...values.map(v => v[0]));
  const lo = Math.min(0, ...values.map(v => v[1])), hi = Math.max(1, ...values.map(v => v[1]));
  const x = (v: number) => 65 + (v - xMin) / (xMax - xMin || 1) * 630;
  const y = (v: number) => 265 - (v - lo) / (hi - lo || 1) * 215;
  let grid = '';
  for (let i = 0; i <= 4; i++) {const v = lo + (hi-lo)*i/4; grid += `<line class="gridline" x1="65" x2="695" y1="${y(v)}" y2="${y(v)}"/><text x="53" y="${y(v)+4}" text-anchor="end">${num(v,1)}</text>`;}
  for (let i = 0; i <= 6; i++) {const v = xMin+(xMax-xMin)*i/6; grid += `<text x="${x(v)}" y="288" text-anchor="middle">${num(v,1)}</text>`;}
  const lines = series.map(s => {let pen = false; const path = s.values.map(([a,b]) => {if (b === null || !Number.isFinite(b)) {pen = false; return '';} const d = `${pen?'L':'M'}${x(a).toFixed(2)},${y(b).toFixed(2)}`; pen = true; return d;}).join(' '); return `<path d="${path}" fill="none" stroke="${s.colour}" stroke-width="2.6" ${s.dashed ? 'stroke-dasharray="6 5"' : ''}/>${s.values.filter(p=>p[1]!==null && Number.isFinite(p[1])).map(([a,b])=>`<circle cx="${x(a)}" cy="${y(b!)}" r="3.5" fill="${s.colour}"><title>${esc(s.label)}: ${num(b)} ${esc(yLabel)} at ${num(a)} ${esc(xLabel)}</title></circle>`).join('')}`;}).join('');
  return `<div class="chart-wrap"><svg class="chart" viewBox="0 0 730 330" role="img" aria-label="${esc(yLabel)} by ${esc(xLabel)}. Exact values are in the table below."><text x="65" y="23">${esc(yLabel)}</text>${grid}${lines}<text x="380" y="321" text-anchor="middle">${esc(xLabel)}</text></svg></div><div class="legend">${series.map(s=>`<span><i style="background:${s.colour}"></i>${esc(s.label)}</span>`).join('')}</div>`;
}
export let localEngine = false;
let token = '';
export async function api(kind: string, body: unknown): Promise<any> {
  if (!localEngine) throw new Error('Open the local workspace to analyse these files. Use “Run on this PC” for setup instructions.');
  const response = await fetch(`./api/${kind}`, {method:'POST', headers:{'Content-Type':'application/json','X-Driftwatch-Token':token}, body:JSON.stringify(body)});
  const result = await response.json(); if (!response.ok) throw new Error(result.error || 'The analysis could not finish.'); return result;
}
export async function readFile(id: string, required = true): Promise<{name:string;text:string}|null> {
  const file = $<HTMLInputElement>(id).files?.[0]; if (!file) {if(required) throw new Error('Choose the required files first.'); return null;}
  if (file.size > 12_000_000) throw new Error(`${file.name} is larger than the 12 MB file limit. Use the command-line analyser for larger files.`);
  return {name:file.name,text:await file.text()};
}
export function setup(): void {$<HTMLDialogElement>('setup-dialog').showModal();}
$('setup-open').onclick = setup; $('setup-close').onclick = () => $<HTMLDialogElement>('setup-dialog').close();

type Lead = {n:number;in_track:{median_km:number;p95_km:number;inside_2_sigma:number|null};storm_term:{n:number;median_abs_raw_km:number|null;median_abs_corrected_km:number|null;improvement:number|null}};
type WindowResult = {n_sets:number;n_trial_leads:number;n_excluded_gap:number;n_excluded_manoeuvre:number;n_excluded_sgp4_error:number;by_lead_h:Record<string,Lead>;role:string};
type Benchmark = {built_at:string;summary:{windows:Record<string,WindowResult>};windows?:Record<string,{sets_from:string;sets_to:string}>;reference_kind?:string;forcing?:string;label?:string;sources?:unknown[]};
let benchmark: Benchmark | null = null;
let selectedWindow = 'storm';
let tolerance = 25;
let imported = false;
let sourceName = 'Swarm A, B and C · ESA reconstructed orbits';
let benchmarkTracks: Record<string,{start:string;end:string;tracks:import('./workspace-globe').Trace[]}> = {};
const titles: Record<string,string> = {quiet:'Quiet control',storm:'May 2024 storm','held-out':'October holdout'};
function normaliseBenchmark(input: any): Benchmark {
  const source = input?.ephemeris ? {built_at:input.built_at,summary:input.ephemeris.summary,label:input.ephemeris.label,reference_kind:input.ephemeris.reference_kind || 'unspecified',forcing:input.forcing || 'unspecified'} : input;
  if (!source?.summary?.windows || !Object.keys(source.summary.windows).length || Object.keys(source.summary.windows).length>20) throw new Error('This file needs a non-empty summary.windows object from driftwatch validate swarm or driftwatch local.');
  for (const w of Object.values(source.summary.windows) as any[]) {
    if(!w.by_lead_h || Object.keys(w.by_lead_h).length>1000) throw new Error('Each window needs a by_lead_h table (at most 1,000 leads).');
    for(const [lead,row] of Object.entries(w.by_lead_h) as [string,any][]) {
      if(!Number.isFinite(Number(lead)) || Number(lead)<0 || !row?.in_track || !row.storm_term || !Number.isInteger(row.n) || row.n<0) throw new Error('A lead row is missing its sample count or comparison fields.');
      for(const n of [row.in_track.median_km,row.in_track.p95_km,row.storm_term.median_abs_raw_km,row.storm_term.median_abs_corrected_km]) if(n!==null && (typeof n!=='number' || !Number.isFinite(n) || n<0)) throw new Error('Distances must be finite, non-negative numbers or null.');
    }
  }
  return source;
}
function weather(): void {
  if(!benchmark) {$('content').innerHTML='<div class="loading-state" role="status">Loading the published benchmark…</div>';return;}
  const names=Object.keys(benchmark.summary.windows);if(!names.includes(selectedWindow)) selectedWindow=names[0];
  const w=benchmark.summary.windows[selectedWindow]; const rows=Object.entries(w.by_lead_h).sort((a,b)=>+a[0]-+b[0]);
  const firstBeyond=rows.find(([,r])=>r.in_track.p95_km!==null && r.in_track.p95_km>tolerance);
  const prefix=firstBeyond?rows.slice(0,rows.indexOf(firstBeyond)):rows;
  const lastWithin=prefix.filter(([,r])=>r.in_track.p95_km!==null && r.in_track.p95_km<=tolerance).at(-1);
  const at72=w.by_lead_h['72'] || rows.at(-1)?.[1]; const leadLabel=w.by_lead_h['72']?'72':rows.at(-1)?.[0] || '—';
  const raw=rows.map(([h,r]):[number,number|null]=>[+h,r.storm_term.median_abs_raw_km]);
  const corrected=rows.map(([h,r]):[number,number|null]=>[+h,r.storm_term.median_abs_corrected_km]);
  const hasCorrection=corrected.some(p=>p[1]!==null);
  const decision=firstBeyond ? `The 95th percentile of along-track disagreement first exceeds your ${num(tolerance)} km tolerance at ${num(+firstBeyond[0],0)} hours. ${lastWithin?`The previous measured lead is ${num(+lastWithin[0],0)} hours.`:'It already exceeds it at the shortest measured lead.'} Ask for a fresher orbit before relying on this tolerance.` : 'No measured lead exceeds this tolerance. This does not establish performance between samples or on another spacecraft.';
  $('content').innerHTML=header('Space weather / model evaluation','Orbit confidence.','Compare a public orbit prediction with a reference, then check whether a storm correction reduces the disagreement.', '<button class="secondary" id="setup-inline">Run on this PC ↗</button><button class="primary" id="export-weather">Export evidence ↓</button>')+
    `<div class="toolbar"><div class="segmented" role="group" aria-label="Benchmark window">${names.map(k=>`<button data-window="${esc(k)}" aria-pressed="${k===selectedWindow}">${esc(imported?k:(titles[k]||k))}</button>`).join('')}</div><label class="input-inline">Your tolerance <input id="tolerance" type="number" min="0.001" max="100000" step="any" value="${tolerance}"/> km</label></div>`+
    `<div class="metrics">${metric('Last sampled lead before the first breach',lastWithin?`${num(+lastWithin[0],0)} <small>hours</small>`:'No usable lead',`95th percentile · ${num(tolerance)} km tolerance`,'good')}${metric(`Typical disagreement at ${esc(leadLabel)} hours`,`${num(at72?.in_track.median_km)} <small>km</small>`,'Median absolute distance along the orbit')}${metric(`Inside the stated 2σ band at ${esc(leadLabel)} hours`,at72?.in_track.inside_2_sigma!=null?`${num(at72.in_track.inside_2_sigma*100,0)}<small>%</small>`:'Not supplied','About 95% expected under a calibrated Gaussian model','warn')}</div>`+
    `<div class="visual-analysis mission-stage">${scene('Earth context · the benchmark below measures historical Swarm orbits')}<section class="card chart-card"><div class="card-head"><div><h2>Does the correction earn its place?</h2><p class="card-sub">Median along-track disagreement · matched trials</p></div><span class="badge amber">${imported?'Imported':'Hindcast'}</span></div>${chart([{label:imported?'Baseline':'Public prediction',colour:'#61dfff',values:hasCorrection?raw:rows.map(([h,r])=>[+h,r.in_track.median_km])},...(hasCorrection?[{label:imported?'Candidate model':'With storm correction',colour:'#c4f563',values:corrected}]:[])],'Prediction lead (hours)','Disagreement (km)')}<div class="decision"><strong>What this changes</strong>${decision}</div></section></div><div class="reference-row">`+
    `<aside class="card card-pad reference-card"><h2>Know the reference</h2><dl class="definition"><dt>Orbit data</dt><dd>${esc(sourceName)}</dd></dl><dl class="definition"><dt>Evaluation</dt><dd>${imported?esc(benchmark.forcing||'Forcing not declared; forecast skill is unverified.'):'Historical replay using observed weather. This measures model behaviour, not the skill of a weather forecast.'}</dd></dl><dl class="definition"><dt>Sample</dt><dd>${num(w.n_sets,0)} element-set epochs · ${num(w.n_trial_leads,0)} set–lead pairs<br/>${imported?'Reference type: '+esc(benchmark.reference_kind||'unspecified'):'Three related spacecraft; not a fleet-wide guarantee.'}</dd></dl></aside></div>`+
    `<details class="card table-card measurement-table"><summary>Inspect the measurements</summary><div class="card-head"><div><h2>The numbers behind the curve</h2><p class="card-sub">Smaller disagreement is better. A correction can also make a prediction worse.</p></div></div><div class="table-scroll"><table><thead><tr><th>Lead</th><th class="numeric">Trials</th><th class="numeric">Median</th><th class="numeric">95th percentile</th><th class="numeric">Corrected median*</th><th>Correction effect*</th></tr></thead><tbody>${rows.map(([h,r])=>`<tr><td>${esc(h)} h</td><td class="numeric">${num(r.n,0)}</td><td class="numeric">${num(r.in_track.median_km)} km</td><td class="numeric ${r.in_track.p95_km>tolerance?'warn':''}">${num(r.in_track.p95_km)} km</td><td class="numeric">${num(r.storm_term.median_abs_corrected_km)}${r.storm_term.n?' km':''}</td><td class="${(r.storm_term.improvement??0)>=0?'good':'bad'}">${r.storm_term.improvement==null?'Not evaluated':`${num(Math.abs(r.storm_term.improvement)*100,0)}% ${r.storm_term.improvement>=0?'better':'worse'}`}</td></tr>`).join('')}</tbody></table></div><div class="decision">*Correction statistics use only trials with a computed storm term. The median column uses every usable trial. Missing values mean “not evaluated”.</div></details>`+
    `<details class="card details-panel"><summary>How to read this without losing the science</summary><div class="details-body"><p>Along-track means forward or backward along the orbit. The median splits the measured disagreements in half; the 95th percentile leaves 5% above it. These are sample statistics, not guaranteed error bounds. Successive orbit fits share observations, so their errors are correlated.</p><p>2σ is twice the estimated standard deviation. If its Gaussian assumptions and scale were right, about 95% of measurements would fit inside that band. Low coverage means the uncertainty estimate is too confident for this sample. Agreement between two predictions cannot establish either one's accuracy.</p><p>Excluded: ${num(w.n_excluded_gap,0)} for missing reference data, ${num(w.n_excluded_manoeuvre,0)} for manoeuvres, ${num(w.n_excluded_sgp4_error,0)} for propagation errors. The task threshold uses uncorrected 95th percentiles and stops at the first breach; no interpolation between lead bins.</p><p>Reference results built ${esc(benchmark.built_at)}. The public benchmark is described in <a href="https://github.com/nikhilb9244-cloud/driftwatch/blob/main/docs/calibration-benchmark.md">the calibration methods</a>.</p></div></details>`+
    `<details class="card details-panel benchmark-import"><summary>Evaluate results from your own PC</summary><div class="details-body"><p>Load a benchmark JSON from <code>driftwatch validate swarm</code> or <code>driftwatch local</code>. This file is read inside the browser. Source labels are declarations, not verified provenance.</p><label class="field">Benchmark JSON<input id="benchmark-file" type="file" accept=".json,application/json"/></label><button id="load-benchmark" class="secondary">Load results</button> <button id="reset-benchmark" class="text-button">Restore public benchmark</button><p id="benchmark-status" role="status"></p><p>For a new paired model experiment, use the <a href="#orbits">orbit comparison tool</a> to evaluate the baseline and candidate OEM against the same reconstructed reference, at the same times. A forecast claim also requires a recorded forecast issue time.</p></div></details>`;
  const stage = document.querySelector('.mission-stage');
  const metrics = document.querySelector('#content > .metrics');
  if (stage && metrics) stage.after(metrics);
  const trace = imported ? undefined : benchmarkTracks[selectedWindow];
  mountScene(trace?.tracks || []);
  if(trace) $('earth-caption').textContent=`ESA reconstructed orbits · ${trace.start.slice(0,10)} · 12:00–13:40 UTC`;
  $('content').insertAdjacentHTML('beforeend', `<details class="card details-panel"><summary>Run a paired model experiment from a CSV</summary><div class="details-body"><p>Supply one row per paired trial and lead. The same reference must be used for the baseline and candidate. Distances are signed along-track residuals in km. A holdout label alone does not prove independence from model tuning.</p><form id="model-form"><label class="field">Trial CSV<input id="model-trials" type="file" accept=".csv" required/><small>trial_id,satellite,window,lead_h,baseline_km,candidate_km. Optional sigma_km. Forecast trials also need issued_at,valid_at (UTC).</small></label><div class="field-row"><label class="field">Reference type<select id="model-reference" required><option value="">Choose its meaning</option><option value="reconstructed">Reconstructed orbit</option><option value="navigation">Navigation solution</option><option value="prediction">Another prediction</option></select></label><label class="field">Weather input<select id="model-forcing"><option value="observed">Observed weather · hindcast</option><option value="forecast">Recorded forecast · issue times required</option></select></label></div><button id="run-model" class="primary" type="submit">Evaluate paired trials →</button><p id="model-status" role="status"></p></form><p>Runs in the local Python engine. Exclusion reasons must be recorded upstream; this CSV tool does not infer missing observations or manoeuvres.</p></div></details>`);
  $('model-form').onsubmit=async(e)=>{e.preventDefault();const button=$<HTMLButtonElement>('run-model'),status=$('model-status');button.disabled=true;status.textContent='Evaluating paired trials locally…';try{const f=await readFile('model-trials');const result=await api('model',{trials:f,reference_kind:$<HTMLSelectElement>('model-reference').value,forcing:$<HTMLSelectElement>('model-forcing').value});if(!document.contains(status))return;benchmark=normaliseBenchmark(result);imported=true;sourceName=f!.name;weather();}catch(err){status.textContent=(err as Error).message;}finally{button.disabled=false;}};
  $('setup-inline').textContent=localEngine?'Compare your files ↗':'Use your own data ↗';
  $('setup-inline').onclick=localEngine?()=>{location.hash='orbits';}:setup;
  document.querySelectorAll<HTMLButtonElement>('[data-window]').forEach(b=>b.onclick=()=>{selectedWindow=b.dataset.window!;weather();});
  $('tolerance').onchange=()=>{const value=$<HTMLInputElement>('tolerance').valueAsNumber;if(Number.isFinite(value)&&value>=.001&&value<=100000){tolerance=value;weather();}else $<HTMLInputElement>('tolerance').reportValidity();};
  $('export-weather').onclick=()=>download('driftwatch-model-evidence.json',{...benchmark,review:{window:selectedWindow,tolerance_km:tolerance,source_label:sourceName,first_measured_breach_h:firstBeyond?+firstBeyond[0]:null,last_measured_lead_before_breach_h:lastWithin?+lastWithin[0]:null,imported,warning:'Empirical comparison; no operational safety guarantee.'}});
  $('load-benchmark').onclick=async()=>{try{const f=await readFile('benchmark-file');const next=normaliseBenchmark(JSON.parse(f!.text));benchmark=next;sourceName=f!.name;imported=true;weather();}catch(e){$('benchmark-status').textContent=(e as Error).message;}};
  $('reset-benchmark').onclick=async()=>{await loadPublic();weather();};
}
async function loadPublic(): Promise<void> {const r=await fetch('./examples/benchmark.json');if(!r.ok)throw new Error('The reference benchmark could not be loaded.');benchmark=normaliseBenchmark(await r.json());imported=false;sourceName='Swarm A, B and C · ESA reconstructed orbits';try{const t=await fetch('./examples/benchmark-tracks.json');if(t.ok)benchmarkTracks=(await t.json()).windows;}catch{benchmarkTracks={};}}
const labels:Record<string,string>={weather:'Storm models',orbits:'Compare orbits',contacts:'Ground contacts',evidence:'Evidence lab'};
function route(): void {const view=location.hash.slice(1) in labels?location.hash.slice(1):'weather';$('view-label').textContent=labels[view];document.querySelectorAll<HTMLAnchorElement>('[data-view]').forEach(a=>{if(a.dataset.view===view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});if(view==='weather')weather();else renderTool(view);}
window.addEventListener('hashchange',route);
async function initialise():Promise<void>{try{const r=await fetch('./api/health');if(r.ok && r.headers.get('content-type')?.includes('application/json')){const h=await r.json();if(h.service==='driftwatch-local'&&h.token){localEngine=true;token=h.token;}}}catch{/* A static site intentionally has no engine. */}$('connection-label').textContent=localEngine?'Local engine connected':'Public reference mode';$('connection-dot').classList.toggle('online',localEngine);try{await loadPublic();route();}catch(e){$('content').innerHTML=`<div class="error" role="alert">${esc((e as Error).message)}</div>`;}}
void initialise();




