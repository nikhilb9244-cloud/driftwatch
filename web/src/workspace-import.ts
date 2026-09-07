import { $, api, esc, localEngine, readFile } from './workspace';

const keys = ['EPOCH', 'X', 'Y', 'Z', 'X_DOT', 'Y_DOT', 'Z_DOT'];
const labels = ['Time', 'X position', 'Y position', 'Z position', 'X velocity', 'Y velocity', 'Z velocity'];
const value = (id: string) => (document.getElementById(id) as HTMLInputElement | HTMLSelectElement | null)?.value || '';
export function importOptions(id: string): Record<string, unknown> {
  const delimiter = value(`${id}-delimiter`) === 'tab' ? '\t' : value(`${id}-delimiter`) || ',';
  if (value(`${id}-format`) !== 'state-csv') return {delimiter};
  return {format: 'state-csv', delimiter, frame: value(`${id}-frame`), time_system: value(`${id}-clock`),
    position_unit: value(`${id}-position-unit`), velocity_unit: value(`${id}-velocity-unit`), object_id: value(`${id}-identity`),
    columns: Object.fromEntries(keys.map(k => [k, value(`${id}-map-${k}`)]))};
}
export function tableHeadings(text: string, delimiter: string): string[] {
  const row = text.replace(/^\uFEFF/, '').split(/\r?\n/)[0];
  const cells: string[] = []; let cell = '', quoted = false;
  for (let i = 0; i < row.length; i++) {
    if (row[i] === '"') { if (quoted && row[i + 1] === '"') { cell += '"'; i++; } else quoted = !quoted; }
    else if (row[i] === delimiter && !quoted) { cells.push(cell); cell = ''; }
    else cell += row[i];
  }
  cells.push(cell); return cells.slice(0, 100);
}
const select = (id: string, label: string, values: [string, string][]) => `<label class="field">${label}<select id="${id}">${values.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('')}</select></label>`;
export function prepareImports(ids: string[]): void {
  for (const id of ids) {
    const input = document.getElementById(id) as HTMLInputElement | null;
    if (!input) continue;
    input.accept = '.oem,.omm,.kvn,.xml,.json,.csv,.tsv,.tle,.txt';
    const host = document.createElement('div'); host.className = 'import-options';
    host.innerHTML = `<details><summary>Format and column mapping</summary>${select(`${id}-format`, 'Input format', [['auto', 'Detect exchange format'], ['state-csv', 'Custom state CSV / TSV']])}${select(`${id}-delimiter`, 'Table separator', [[',', 'Comma'], [';', 'Semicolon'], ['tab', 'Tab']])}<div id="${id}-mapping" hidden><p>Declare the conventions used by your exporter. These values are never inferred from the trajectory.</p><div id="${id}-columns"></div>${select(`${id}-frame`, 'Coordinate frame', [['', 'Choose frame'], ['TEME', 'TEME · SGP4 frame'], ['J2000', 'J2000 · inertial'], ['ITRF', 'ITRF · Earth-fixed']])}${select(`${id}-clock`, 'Time system', [['', 'Choose clock'], ['UTC', 'UTC'], ['GPS', 'GPS'], ['TAI', 'TAI']])}<div class="field-row">${select(`${id}-position-unit`, 'Position units', [['', 'Choose units'], ['km', 'Kilometres'], ['m', 'Metres']])}${select(`${id}-velocity-unit`, 'Velocity units', [['', 'Choose units'], ['km/s', 'km/s'], ['m/s', 'm/s']])}</div><label class="field">Spacecraft OBJECT_ID<input id="${id}-identity" placeholder="e.g. 2024-001A" maxlength="80"/><small>Use the same identifier in the reference and predictions.</small></label></div></details><button type="button" class="text-button" id="${id}-inspect">Check this file</button><div id="${id}-preview" class="import-preview" role="status" hidden></div>`;
    input.closest('label')!.after(host);
    let version = 0;
    const map = async () => {
      const serial = ++version;
      $(`${id}-mapping`).hidden = value(`${id}-format`) !== 'state-csv';
      const file = input.files?.[0]; if (!file || file.size > 12_000_000) return;
      const text = await file.text(); if (serial !== version || !document.contains(host)) return;
      const columns = tableHeadings(text, value(`${id}-delimiter`) === 'tab' ? '\t' : value(`${id}-delimiter`));
      $(`${id}-columns`).innerHTML = keys.map((key, i) => select(`${id}-map-${key}`, labels[i], [['', 'Select a column'], ...columns.map(c => [c, c] as [string, string])])).join('');
      const aliases = [['epoch', 'time', 'timestamp', 'utc'], ['x', 'x_km', 'x_m'], ['y', 'y_km', 'y_m'], ['z', 'z_km', 'z_m'], ['x_dot', 'vx', 'vx_kms', 'vx_ms'], ['y_dot', 'vy', 'vy_kms', 'vy_ms'], ['z_dot', 'vz', 'vz_kms', 'vz_ms']];
      keys.forEach((key, i) => { ($(`${id}-map-${key}`) as HTMLSelectElement).value = columns.find(c => aliases[i].includes(c.toLowerCase())) || ''; });
    };
    const inspect = async () => {
      const serial = ++version, out = $(`${id}-preview`), button = $(`${id}-inspect`) as HTMLButtonElement;
      out.hidden = false; button.disabled = true; out.textContent = 'Checking the format and declared conventions…';
      try {
        const file = await readFile(id);
        if (!localEngine) throw new Error('File selected. Open the local workspace to validate its format, frame, clock and coverage. No file has been uploaded.');
        const result = await api('inspect', {file, options: importOptions(id)});
        if (serial !== version || !document.contains(out)) return;
        out.innerHTML = `<strong>${esc(result.format)} · supported fields checked</strong>${esc(result.frame)} / ${esc(result.time_system)}${result.object_id ? ' / ' + esc(result.object_id) : ''}<br/>${esc(result.start)} → ${esc(result.end)}<br/>${esc(result.coverage_label)}${(result.warnings || []).map((w: string) => `<p>${esc(w)}</p>`).join('')}<small>Publisher and reference quality are not verified.</small>`;
        if (result.objects?.length) {
          out.insertAdjacentHTML('beforeend', select(`${id}-object`, 'Catalogue object for this analysis', result.objects.map((o: any) => [String(o.norad), `${o.norad} · ${o.name || 'Unnamed'}`])));
          const picker = $(`${id}-object`) as HTMLSelectElement;
          const norad = document.getElementById('norad') as HTMLInputElement | null;
          if (norad && result.objects.some((o: any) => String(o.norad) === norad.value)) picker.value = norad.value;
          else if (norad && result.objects.length === 1) norad.value = picker.value;
          else picker.insertAdjacentHTML('afterbegin', '<option value="" selected>Select an object</option>');
          picker.onchange = () => { if (norad && picker.value) norad.value = picker.value; };
        }
      } catch (error) { if (serial === version && document.contains(out)) out.textContent = (error as Error).message; }
      finally { button.disabled = false; }
    };
    input.onchange = async () => { await map(); await inspect(); };
    $(`${id}-format`).onchange = () => { void map(); $(`${id}-preview`).hidden = true; };
    $(`${id}-delimiter`).onchange = () => { void map(); $(`${id}-preview`).hidden = true; };
    host.addEventListener('change', event => {
      const changed = (event.target as HTMLElement).id;
      if (changed !== `${id}-object`) $(`${id}-preview`).hidden = true;
      if (![`${id}-object`, `${id}-format`, `${id}-delimiter`].includes(changed)) version++;
    });
    $(`${id}-inspect`).onclick = () => { void inspect(); };
  }
}
